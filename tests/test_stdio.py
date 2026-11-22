"""End-to-end test: run the server as an MCP client launches it, over stdio."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any

import pytest

ISSUE = {
    "id": "2-1",
    "idReadable": "OPS-1",
    "summary": "Printer is on fire",
    "project": {"id": "0-1", "name": "Operations", "shortName": "OPS"},
    "customFields": [],
}


class FakeYouTrack(BaseHTTPRequestHandler):
    """Answers the one issue the test reads, and 404 for anything else."""

    def do_GET(self) -> None:  # noqa: N802 - name fixed by BaseHTTPRequestHandler
        if self.path.startswith("/api/issues/OPS-1?"):
            body = json.dumps(ISSUE).encode()
            self.send_response(200)
        else:
            body = b'{"error": "not found"}'
            self.send_response(404)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002, ARG002
        return


@pytest.fixture
def youtrack_url() -> Iterator[str]:
    server = HTTPServer(("127.0.0.1", 0), FakeYouTrack)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()


class StdioClient:
    """Speaks newline-delimited JSON-RPC to the server process."""

    def __init__(self, proc: subprocess.Popen[str]) -> None:
        self.proc = proc
        self.next_id = 1

    def send(self, method: str, params: dict[str, Any] | None = None) -> None:
        message: dict[str, Any] = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            message["params"] = params
        self._write(message)

    def request(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        request_id = self.next_id
        self.next_id += 1
        self._write({"jsonrpc": "2.0", "id": request_id, "method": method, "params": params or {}})
        assert self.proc.stdout is not None
        while True:
            line = self.proc.stdout.readline()
            if not line:
                stderr = self.proc.stderr.read() if self.proc.stderr else ""
                pytest.fail(f"server closed stdout before answering {method}:\n{stderr}")
            reply: dict[str, Any] = json.loads(line)
            if reply.get("id") == request_id:
                assert "error" not in reply, reply["error"]
                result: dict[str, Any] = reply["result"]
                return result

    def _write(self, message: dict[str, Any]) -> None:
        assert self.proc.stdin is not None
        self.proc.stdin.write(json.dumps(message) + "\n")
        self.proc.stdin.flush()


def test_handshake_lists_tools_and_reads_an_issue(youtrack_url: str) -> None:
    env = {**os.environ, "YOUTRACK_URL": youtrack_url, "YOUTRACK_TOKEN": "test-token"}
    proc = subprocess.Popen(
        [sys.executable, "-m", "mcp_youtrack"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
    )
    try:
        client = StdioClient(proc)
        init = client.request(
            "initialize",
            {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "0"},
            },
        )
        assert init["serverInfo"]["name"] == "youtrack"
        client.send("notifications/initialized")

        tools = {tool["name"] for tool in client.request("tools/list")["tools"]}
        assert {"search_issues", "get_issue", "create_issue", "list_projects"} <= tools

        called = client.request("tools/call", {"name": "get_issue", "arguments": {"issue_id": "OPS-1"}})
        issue = json.loads(called["content"][0]["text"])
        assert issue["id"] == "OPS-1"
        assert issue["summary"] == "Printer is on fire"
    finally:
        proc.kill()
        proc.wait()
