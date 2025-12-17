# MCP YouTrack

A Model Context Protocol (MCP) server for integrating YouTrack issue tracking with MCP-compatible clients.

## Features

- **Issue Management**: Search, create, update, and delete issues
- **Project Access**: List projects and retrieve custom field definitions
- **Comments**: Add and list comments on issues
- **Issue Linking**: Create dependencies and relationships between issues
- **Flexible Configuration**: Environment-based configuration with SSL options

## Quick Start

### Prerequisites

- Python 3.10+
- [uv](https://github.com/astral-sh/uv) (recommended) or pip
- YouTrack instance with API access
- YouTrack permanent token

### Installation

```bash
# Clone the repository
git clone https://github.com/dsswift/mcp-youtrack.git
cd mcp-youtrack

# Install with uv (recommended)
uv sync

# Or with pip
pip install -e .
```

### Configuration

1. Copy the sample configuration:
   ```bash
   cp .env.sample .env
   ```

2. Edit `.env` with your YouTrack credentials:
   ```bash
   YOUTRACK_URL=https://youtrack.example.com
   YOUTRACK_TOKEN=perm:your-token-here
   ```

3. Generate a permanent token in YouTrack:
   - Go to your YouTrack profile
   - Navigate to Account Security
   - Create a new permanent token with "YouTrack" scope

### Running the Server

```bash
# Run directly with uv
uv run mcp-youtrack

# Or run as a module
python -m mcp_youtrack
```

### Register with Claude Code

```bash
# Using uvx (recommended for portable installation)
claude mcp add youtrack --scope user \
  -e YOUTRACK_URL=https://youtrack.example.com \
  -e YOUTRACK_TOKEN=perm:your-token \
  -- uvx --from /path/to/mcp-youtrack mcp-youtrack

# Or with local installation
claude mcp add youtrack --scope user \
  -e YOUTRACK_URL=https://youtrack.example.com \
  -e YOUTRACK_TOKEN=perm:your-token \
  -- uv run mcp-youtrack
```

### Other MCP Clients

Add to your MCP client configuration:

```json
{
  "mcpServers": {
    "youtrack": {
      "command": "uvx",
      "args": ["--from", "/path/to/mcp-youtrack", "mcp-youtrack"],
      "env": {
        "YOUTRACK_URL": "https://youtrack.example.com",
        "YOUTRACK_TOKEN": "perm:your-token"
      }
    }
  }
}
```

## Available Tools

### Issue Operations

| Tool | Description |
|------|-------------|
| `search_issues` | Search issues with filters (project, assignee, state, domain, query) |
| `get_issue` | Get detailed information about a specific issue |
| `create_issue` | Create a new issue in a project |
| `update_issue` | Update issue fields (summary, description, state, assignee, domain) |
| `delete_issue` | Permanently delete an issue |

### Project Operations

| Tool | Description |
|------|-------------|
| `list_projects` | List all accessible projects |
| `get_project_fields` | Get custom field definitions for a project |

### Comment Operations

| Tool | Description |
|------|-------------|
| `add_comment` | Add a comment to an issue |
| `list_comments` | Get all comments on an issue |

### Issue Linking

| Tool | Description |
|------|-------------|
| `list_link_types` | Get available link types (Depend, Duplicate, Relate, Subtask) |
| `list_issue_links` | Get all links for an issue |
| `add_issue_link` | Create a link between two issues |
| `remove_issue_link` | Remove a link between issues |

## Usage Examples

### Search Issues

```python
# Search all issues in a project
search_issues(project="OPS")

# Search by assignee and state
search_issues(assignee="jsmith", state="In Progress")

# Use YouTrack query syntax
search_issues(query="#Unresolved created: today")
```

### Create an Issue

```python
create_issue(
    project="OPS",
    summary="Fix login timeout issue",
    description="Users are experiencing timeouts when logging in during peak hours."
)
```

### Update Issue State

```python
update_issue(
    issue_id="OPS-123",
    state="In Progress",
    assignee="jsmith"
)
```

### Link Issues

```python
# Create a dependency
add_issue_link("OPS-123", "OPS-456", "Depend")  # OPS-123 depends on OPS-456

# Mark as duplicate
add_issue_link("OPS-789", "OPS-123", "Duplicate")
```

## Configuration Options

| Environment Variable | Required | Default | Description |
|---------------------|----------|---------|-------------|
| `YOUTRACK_URL` | Yes | - | YouTrack instance URL (without trailing slash) |
| `YOUTRACK_TOKEN` | Yes | - | Permanent API token (`perm:...` format) |
| `YOUTRACK_DEFAULT_PROJECT` | No | - | Default project for issue creation |
| `YOUTRACK_TIMEOUT` | No | 30 | Request timeout in seconds |
| `YOUTRACK_VERIFY_SSL` | No | true | SSL certificate verification (`false` for self-signed) |

## Development

### Setup Development Environment

```bash
# Install with dev dependencies
uv sync --all-extras

# Run linting
uv run ruff check src/ tests/

# Run type checking
uv run mypy src/

# Run tests
uv run pytest tests/ -v

# Run tests with coverage
uv run pytest tests/ --cov=mcp_youtrack --cov-report=html
```

### Verify Tools Against Live Instance

```bash
# With .env file
python scripts/verify_tools.py --project TEST

# With environment variables
YOUTRACK_URL=https://youtrack.example.com \
YOUTRACK_TOKEN=perm:xxx \
python scripts/verify_tools.py --project TEST
```

### Project Structure

```
mcp-youtrack/
├── src/mcp_youtrack/
│   ├── __init__.py      # Package entry point
│   ├── __main__.py      # CLI entry point
│   ├── config.py        # Configuration management
│   ├── models.py        # Pydantic data models
│   ├── client.py        # YouTrack API client
│   └── server.py        # FastMCP server implementation
├── tests/               # Unit tests
├── scripts/             # Utility scripts
│   ├── verify_tools.py  # Integration test script
│   └── import-github-issues.py  # GitHub migration script
├── pyproject.toml       # Project configuration
└── .env.sample          # Sample environment configuration
```

## Scripts

### verify_tools.py

Tests all MCP tools against a live YouTrack instance:

```bash
python scripts/verify_tools.py --project OPS
```

### import-github-issues.py

Migrates open GitHub issues to YouTrack:

```bash
# Dry run
python scripts/import-github-issues.py --project OPS --dry-run

# Import issues
python scripts/import-github-issues.py --project OPS

# With domain mapping
python scripts/import-github-issues.py --project OPS --domain-map domains.json
```

Domain mapping file format:
```json
{
  "security": "Security",
  "infrastructure": "Infrastructure",
  "frontend": "UI/UX"
}
```

## License

MIT License - see LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit issues and pull requests.
