#!/usr/bin/env python3
"""Verification script for MCP YouTrack tools.

This script tests all MCP tools against a live YouTrack instance to verify
functionality before and after refactoring. It creates temporary test issues
and cleans them up afterward.

Usage:
    # With .env file in project root:
    python scripts/verify_tools.py

    # With explicit env vars:
    YOUTRACK_URL=https://youtrack.example.com YOUTRACK_TOKEN=xxx python scripts/verify_tools.py

    # Load from MCP config files:
    python scripts/verify_tools.py --load-mcp-config

    # Specify a test project:
    python scripts/verify_tools.py --project OPS
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def load_mcp_config() -> None:
    """Load environment from MCP config if available."""
    mcp_config_paths = [
        Path.cwd() / ".mcp.json",
        Path.home() / ".config" / "mcp" / "config.json",
    ]

    for config_path in mcp_config_paths:
        if config_path.exists():
            try:
                with open(config_path) as f:
                    config = json.load(f)
                    servers = config.get("mcpServers", {})
                    youtrack = servers.get("youtrack", {})
                    env = youtrack.get("env", {})
                    for key, value in env.items():
                        if key not in os.environ:
                            os.environ[key] = value
                    if env:
                        print(f"Loaded config from {config_path}")
                        return
            except Exception as e:
                print(f"Warning: Could not load {config_path}: {e}")


from mcp_youtrack.server import (
    add_comment,
    add_issue_link,
    create_issue,
    delete_issue,
    get_issue,
    get_project_fields,
    list_comments,
    list_issue_links,
    list_link_types,
    list_projects,
    mcp,
    remove_issue_link,
    search_issues,
    update_issue,
)
from mcp_youtrack.client import YouTrackClient
from mcp_youtrack.config import load_config


class ToolVerifier:
    """Runs verification tests on MCP tools."""

    def __init__(self, test_project: str) -> None:
        self.test_project = test_project
        self.created_issues: list[str] = []
        self.results: dict[str, dict] = {}

    def record(self, tool_name: str, success: bool, message: str = "") -> None:
        """Record a test result."""
        self.results[tool_name] = {"success": success, "message": message}
        status = "PASS" if success else "FAIL"
        print(f"  [{status}] {tool_name}: {message if message else 'OK'}")

    async def verify_list_projects(self) -> None:
        """Test list_projects tool."""
        try:
            result = await list_projects()
            data = json.loads(result)
            if "error" in data:
                self.record("list_projects", False, data["error"])
            elif data.get("count", 0) > 0:
                self.record("list_projects", True, f"Found {data['count']} projects")
            else:
                self.record("list_projects", False, "No projects found")
        except Exception as e:
            self.record("list_projects", False, str(e))

    async def verify_get_project_fields(self) -> None:
        """Test get_project_fields tool."""
        try:
            result = await get_project_fields(self.test_project)
            data = json.loads(result)
            if "error" in data:
                self.record("get_project_fields", False, data["error"])
            elif "fields" in data:
                self.record("get_project_fields", True, f"Found {len(data['fields'])} fields")
            else:
                self.record("get_project_fields", False, "No fields returned")
        except Exception as e:
            self.record("get_project_fields", False, str(e))

    async def verify_search_issues(self) -> None:
        """Test search_issues tool with various filters."""
        try:
            # Basic search
            result = await search_issues(project=self.test_project, limit=5)
            data = json.loads(result)
            if "error" in data:
                self.record("search_issues", False, data["error"])
            else:
                self.record("search_issues", True, f"Found {data['count']} issues")

            # Search with state filter
            result = await search_issues(project=self.test_project, state="Open", limit=3)
            data = json.loads(result)
            if "error" not in data:
                self.record("search_issues (state)", True, "State filter works")
            else:
                self.record("search_issues (state)", False, data["error"])

        except Exception as e:
            self.record("search_issues", False, str(e))

    async def verify_create_issue(self) -> str | None:
        """Test create_issue tool. Returns created issue ID."""
        try:
            result = await create_issue(
                project=self.test_project,
                summary="[TEST] MCP Tool Verification - Delete Me",
                description="This is a test issue created by verify_tools.py. Safe to delete.",
            )
            data = json.loads(result)
            if "error" in data:
                self.record("create_issue", False, data["error"])
                return None
            elif data.get("_created") and data.get("id"):
                issue_id = data["id"]
                self.created_issues.append(issue_id)
                self.record("create_issue", True, f"Created {issue_id}")
                return issue_id
            else:
                self.record("create_issue", False, "No issue ID returned")
                return None
        except Exception as e:
            self.record("create_issue", False, str(e))
            return None

    async def verify_get_issue(self, issue_id: str) -> None:
        """Test get_issue tool."""
        try:
            result = await get_issue(issue_id)
            data = json.loads(result)
            if "error" in data:
                self.record("get_issue", False, data["error"])
            elif data.get("id") == issue_id:
                self.record("get_issue", True, f"Retrieved {issue_id}")
            else:
                self.record("get_issue", False, "Issue ID mismatch")
        except Exception as e:
            self.record("get_issue", False, str(e))

    async def verify_update_issue(self, issue_id: str) -> None:
        """Test update_issue tool."""
        try:
            result = await update_issue(
                issue_id=issue_id,
                summary="[TEST] MCP Tool Verification - Updated",
            )
            data = json.loads(result)
            if "error" in data:
                self.record("update_issue", False, data["error"])
            elif data.get("_updated"):
                self.record("update_issue", True, f"Updated {issue_id}")
            else:
                self.record("update_issue", False, "Update flag not set")
        except Exception as e:
            self.record("update_issue", False, str(e))

    async def verify_add_comment(self, issue_id: str) -> None:
        """Test add_comment tool."""
        try:
            result = await add_comment(
                issue_id=issue_id,
                text="Test comment from verify_tools.py",
            )
            data = json.loads(result)
            if "error" in data:
                self.record("add_comment", False, data["error"])
            elif data.get("_created"):
                self.record("add_comment", True, f"Added comment to {issue_id}")
            else:
                self.record("add_comment", False, "Comment not created")
        except Exception as e:
            self.record("add_comment", False, str(e))

    async def verify_list_comments(self, issue_id: str) -> None:
        """Test list_comments tool."""
        try:
            result = await list_comments(issue_id)
            data = json.loads(result)
            if "error" in data:
                self.record("list_comments", False, data["error"])
            elif "comments" in data:
                self.record("list_comments", True, f"Found {data['count']} comments")
            else:
                self.record("list_comments", False, "No comments array")
        except Exception as e:
            self.record("list_comments", False, str(e))

    async def verify_list_link_types(self) -> None:
        """Test list_link_types tool."""
        try:
            result = await list_link_types()
            data = json.loads(result)
            if "error" in data:
                self.record("list_link_types", False, data["error"])
            elif data.get("count", 0) > 0:
                self.record("list_link_types", True, f"Found {data['count']} link types")
            else:
                self.record("list_link_types", False, "No link types found")
        except Exception as e:
            self.record("list_link_types", False, str(e))

    async def verify_issue_links(self, issue_id1: str, issue_id2: str) -> None:
        """Test add_issue_link, list_issue_links, remove_issue_link tools."""
        # Add link
        try:
            result = await add_issue_link(issue_id1, issue_id2, "Relate")
            data = json.loads(result)
            if "error" in data:
                self.record("add_issue_link", False, data["error"])
            elif data.get("success"):
                self.record("add_issue_link", True, f"Linked {issue_id1} -> {issue_id2}")
            else:
                self.record("add_issue_link", False, "Link not created")
        except Exception as e:
            self.record("add_issue_link", False, str(e))

        # List links
        try:
            result = await list_issue_links(issue_id1)
            data = json.loads(result)
            if "error" in data:
                self.record("list_issue_links", False, data["error"])
            elif "links" in data:
                self.record("list_issue_links", True, f"Found {data['count']} links")
            else:
                self.record("list_issue_links", False, "No links array")
        except Exception as e:
            self.record("list_issue_links", False, str(e))

        # Remove link
        try:
            result = await remove_issue_link(issue_id1, issue_id2, "Relate")
            data = json.loads(result)
            if "error" in data:
                self.record("remove_issue_link", False, data["error"])
            elif data.get("success"):
                self.record("remove_issue_link", True, f"Unlinked {issue_id1} -> {issue_id2}")
            else:
                self.record("remove_issue_link", False, "Link not removed")
        except Exception as e:
            self.record("remove_issue_link", False, str(e))

    async def verify_delete_issue(self, issue_id: str) -> None:
        """Test delete_issue tool."""
        try:
            result = await delete_issue(issue_id)
            data = json.loads(result)
            if "error" in data:
                self.record("delete_issue", False, data["error"])
            elif data.get("deleted"):
                self.record("delete_issue", True, f"Deleted {issue_id}")
                if issue_id in self.created_issues:
                    self.created_issues.remove(issue_id)
            else:
                self.record("delete_issue", False, "Delete flag not set")
        except Exception as e:
            self.record("delete_issue", False, str(e))

    async def cleanup(self, client: YouTrackClient) -> None:
        """Clean up any remaining test issues."""
        for issue_id in self.created_issues:
            try:
                await client.delete_issue(issue_id)
                print(f"  Cleaned up {issue_id}")
            except Exception as e:
                print(f"  Failed to clean up {issue_id}: {e}")

    async def run_all(self) -> bool:
        """Run all verification tests."""
        print("\n" + "=" * 60)
        print("MCP YouTrack Tool Verification")
        print("=" * 60)

        config = load_config()
        print(f"\nConnecting to: {config.url}")
        print(f"Test project: {self.test_project}\n")

        async with YouTrackClient(config) as client:
            # Inject client into MCP context manually for testing
            # We need to mock the context since we're not running through MCP
            from unittest.mock import MagicMock, patch

            mock_ctx = MagicMock()
            mock_ctx.request_context.lifespan_context = {"client": client, "config": config}

            with patch.object(mcp, 'get_context', return_value=mock_ctx):
                print("Testing read-only tools...")
                await self.verify_list_projects()
                await self.verify_get_project_fields()
                await self.verify_search_issues()
                await self.verify_list_link_types()

                print("\nTesting write tools...")
                issue1 = await self.verify_create_issue()
                issue2 = await self.verify_create_issue()

                if issue1:
                    await self.verify_get_issue(issue1)
                    await self.verify_update_issue(issue1)
                    await self.verify_add_comment(issue1)
                    await self.verify_list_comments(issue1)

                if issue1 and issue2:
                    await self.verify_issue_links(issue1, issue2)

                print("\nTesting delete...")
                if issue1:
                    await self.verify_delete_issue(issue1)
                if issue2:
                    await self.verify_delete_issue(issue2)

                print("\nCleaning up...")
                await self.cleanup(client)

        # Summary
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)

        passed = sum(1 for r in self.results.values() if r["success"])
        total = len(self.results)
        print(f"\nPassed: {passed}/{total}")

        failed = [name for name, r in self.results.items() if not r["success"]]
        if failed:
            print(f"Failed: {', '.join(failed)}")
            return False

        print("\nAll tests passed!")
        return True


async def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Verify MCP YouTrack tools")
    parser.add_argument(
        "--load-mcp-config",
        action="store_true",
        help="Load YouTrack config from MCP config files",
    )
    parser.add_argument(
        "--project",
        default=os.getenv("YOUTRACK_DEFAULT_PROJECT", "TEST"),
        help="Project short name to use for testing (default: TEST or YOUTRACK_DEFAULT_PROJECT)",
    )
    args = parser.parse_args()

    if args.load_mcp_config:
        load_mcp_config()

    verifier = ToolVerifier(args.project)
    success = await verifier.run_all()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
