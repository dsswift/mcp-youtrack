# mcp-youtrack

An MCP server for YouTrack, served over stdio. Read `README.md` for the tools
and configuration.

## Working here

- Python 3.10+, managed with uv. `uv sync --all-extras` sets up the dev
  environment.
- Check: `uv run ruff check src/ tests/`, `uv run mypy src/`, `uv run pytest`.
  All three run in CI (`.github/workflows/ci.yml`) on every push to `main`
  and weekly, against freshly resolved dependencies.
- `tests/test_stdio.py` starts the server the way an MCP client does and
  talks JSON-RPC to it over stdio, against a fake YouTrack. A change to how
  the server starts, its SDK, or its stdout must keep it green.
- stdout carries only protocol messages. Log to stderr.
- Every runtime dependency has an upper bound on its next major version. Users
  install with `uvx`, which ignores any lockfile and takes the newest
  release in range, so an unbounded dependency breaks every install the day
  its next major ships.
- `scripts/verify_tools.py` exercises every tool against a live YouTrack and
  creates and deletes test issues. Run it only against a project made for
  testing.

## Release

There is no versioning. Users install from `main`
(`uvx --from git+https://github.com/dsswift/mcp-youtrack.git mcp-youtrack`),
so a commit on `main` is the release. Land with `release-damnit land` and
watch the `ci` workflow.
