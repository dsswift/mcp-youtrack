"""YouTrack MCP Server with FastMCP tools."""

from __future__ import annotations

import json
import logging
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from mcp.server.fastmcp import FastMCP

from .client import YouTrackClient, YouTrackError, YouTrackNotFoundError
from .config import load_config

# Configure logging to stderr (stdout is reserved for MCP protocol)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_server: FastMCP) -> AsyncIterator[dict[str, Any]]:
    """Manage server lifecycle and shared resources."""
    config = load_config()
    logger.info("YouTrack MCP Server starting, connecting to %s", config.url)

    async with YouTrackClient(config) as client:
        yield {"client": client, "config": config}

    logger.info("YouTrack MCP Server shutting down")


# Initialize FastMCP server
mcp = FastMCP(
    name="youtrack",
    lifespan=lifespan,
)


def format_issue(issue: Any) -> dict[str, Any]:
    """Format an issue for display."""
    result: dict[str, Any] = {
        "id": issue.id_readable or issue.id,
        "summary": issue.summary,
    }

    if issue.description:
        result["description"] = issue.description

    if issue.project:
        result["project"] = issue.project.short_name or issue.project.name

    if issue.reporter:
        result["reporter"] = issue.reporter.name or issue.reporter.login

    if issue.created:
        result["created"] = issue.created.isoformat()

    if issue.updated:
        result["updated"] = issue.updated.isoformat()

    # Extract key custom fields
    for field in issue.custom_fields:
        if field.name and field.value is not None:
            if hasattr(field.value, "name"):
                result[field.name] = field.value.name
            elif isinstance(field.value, list):
                result[field.name] = [
                    v.name if hasattr(v, "name") else str(v) for v in field.value
                ]
            else:
                result[field.name] = field.value

    return result


def format_project(project: Any) -> dict[str, Any]:
    """Format a project for display."""
    return {
        "id": project.id,
        "shortName": project.short_name,
        "name": project.name,
        "description": project.description,
        "archived": project.archived,
    }


def format_comment(comment: Any) -> dict[str, Any]:
    """Format a comment for display."""
    result: dict[str, Any] = {
        "id": comment.id,
        "text": comment.text,
    }

    if comment.author:
        result["author"] = comment.author.name or comment.author.login

    if comment.created:
        result["created"] = comment.created.isoformat()

    if comment.updated:
        result["updated"] = comment.updated.isoformat()

    return result


@mcp.tool()
async def search_issues(
    project: str | None = None,
    assignee: str | None = None,
    state: str | None = None,
    domain: str | None = None,
    query: str | None = None,
    limit: int = 25,
) -> str:
    """Search for issues in YouTrack.

    Args:
        project: Project short name to filter by (e.g., 'OPS').
        assignee: Filter by assignee username (e.g., 'jsmith', 'tbellerive').
        state: Filter by state name (e.g., 'In Progress', 'Open', 'Done').
        domain: Filter by domain (e.g., 'Administrative', 'Security', 'Microsoft 365').
        query: Additional YouTrack search query (e.g., '#Unresolved', 'created: today').
        limit: Maximum number of results to return (default 25, max 100).

    Returns:
        JSON array of matching issues with key fields.

    Examples:
        - search_issues(project="OPS") - All issues in OPS project
        - search_issues(assignee="tbellerive", state="In Progress") - User's in-progress tasks
        - search_issues(project="HD", state="New") - New issues in HD project
        - search_issues(domain="Security") - All Security domain issues
        - search_issues(query="#Unresolved") - All unresolved issues
    """
    ctx = mcp.get_context()
    client: YouTrackClient = ctx.request_context.lifespan_context["client"]

    limit = min(max(1, limit), 100)  # Clamp between 1 and 100

    # Build the query using correct YouTrack syntax
    query_parts: list[str] = []
    if assignee:
        query_parts.append(f"for: {assignee}")
    if state:
        # Use #{State} syntax for states with spaces
        if " " in state:
            query_parts.append(f"#{{{state}}}")
        else:
            query_parts.append(f"#{state}")
    if domain:
        # Use Domain: {value} syntax for domain field
        if " " in domain:
            query_parts.append(f"Domain: {{{domain}}}")
        else:
            query_parts.append(f"Domain: {domain}")
    if query:
        query_parts.append(query)

    built_query = " ".join(query_parts) if query_parts else None

    try:
        issues = await client.list_issues(
            project=project,
            query=built_query,
            limit=limit,
        )

        # Build display query for response
        display_parts: list[str] = []
        if project:
            display_parts.append(f"project: {project}")
        if built_query:
            display_parts.append(built_query)
        display_query = " ".join(display_parts) if display_parts else None

        result = {
            "count": len(issues),
            "query": display_query,
            "issues": [format_issue(issue) for issue in issues],
        }

        return json.dumps(result, indent=2, default=str)

    except YouTrackError as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def get_issue(issue_id: str) -> str:
    """Get detailed information about a specific issue.

    Args:
        issue_id: The issue ID (e.g., 'OPS-123' or database ID).

    Returns:
        JSON object with full issue details.
    """
    ctx = mcp.get_context()
    client: YouTrackClient = ctx.request_context.lifespan_context["client"]

    try:
        issue = await client.get_issue(issue_id)
        return json.dumps(format_issue(issue), indent=2, default=str)

    except YouTrackNotFoundError:
        return json.dumps({"error": f"Issue '{issue_id}' not found"})
    except YouTrackError as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def create_issue(
    summary: str,
    description: str | None = None,
    project: str | None = None,
) -> str:
    """Create a new issue in YouTrack.

    Args:
        summary: Issue title/summary (required).
        description: Detailed description of the issue (optional, supports markdown).
        project: Project short name (e.g., 'OPS'). Uses YOUTRACK_DEFAULT_PROJECT if not specified.

    Returns:
        JSON object with the created issue details including the new issue ID.
    """
    ctx = mcp.get_context()
    client: YouTrackClient = ctx.request_context.lifespan_context["client"]
    config = ctx.request_context.lifespan_context["config"]

    # Use default project if not specified
    target_project = project or config.default_project
    if not target_project:
        return json.dumps({
            "error": "No project specified and YOUTRACK_DEFAULT_PROJECT not configured"
        })

    try:
        # First, get the project to get its database ID
        project_obj = await client.get_project(target_project)

        issue = await client.create_issue(
            project_id=project_obj.id,
            summary=summary,
            description=description,
        )

        result = format_issue(issue)
        result["_created"] = True

        return json.dumps(result, indent=2, default=str)

    except YouTrackNotFoundError:
        return json.dumps({"error": f"Project '{target_project}' not found"})
    except YouTrackError as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def update_issue(
    issue_id: str,
    summary: str | None = None,
    description: str | None = None,
    state: str | None = None,
    assignee: str | None = None,
    domain: str | None = None,
) -> str:
    """Update an existing issue in YouTrack.

    Args:
        issue_id: The issue ID to update (e.g., 'OPS-123').
        summary: New issue summary/title (optional).
        description: New issue description (optional).
        state: New state name (e.g., 'Open', 'In Progress', 'Done') (optional).
        assignee: Assignee login name (optional).
        domain: Domain name (e.g., 'Administrative', 'Security') (optional).

    Returns:
        JSON object with the updated issue details.
    """
    ctx = mcp.get_context()
    client: YouTrackClient = ctx.request_context.lifespan_context["client"]

    try:
        # Handle state, assignee, and domain via commands
        if state or assignee or domain:
            commands: list[str] = []
            if state:
                commands.append(f"State: {state}")
            if assignee:
                commands.append(f"Assignee: {assignee}")
            if domain:
                commands.append(f"Domain: {domain}")

            await client.execute_command(issue_id, " ".join(commands))

        # Handle direct field updates
        if summary is not None or description is not None:
            issue = await client.update_issue(
                issue_id=issue_id,
                summary=summary,
                description=description,
            )
        else:
            # Fetch the updated issue
            issue = await client.get_issue(issue_id)

        result = format_issue(issue)
        result["_updated"] = True

        return json.dumps(result, indent=2, default=str)

    except YouTrackNotFoundError:
        return json.dumps({"error": f"Issue '{issue_id}' not found"})
    except YouTrackError as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def delete_issue(issue_id: str) -> str:
    """Delete an issue from YouTrack.

    WARNING: This operation cannot be undone. The issue will be permanently deleted.

    Args:
        issue_id: The issue ID to delete (e.g., 'OPS-123').

    Returns:
        JSON object confirming deletion or error message.
    """
    ctx = mcp.get_context()
    client: YouTrackClient = ctx.request_context.lifespan_context["client"]

    try:
        # Get the issue first to confirm it exists and capture details
        issue = await client.get_issue(issue_id)
        issue_summary = issue.summary

        await client.delete_issue(issue_id)

        return json.dumps(
            {
                "deleted": True,
                "issue_id": issue_id,
                "summary": issue_summary,
                "message": f"Issue {issue_id} has been permanently deleted",
            },
            indent=2,
        )

    except YouTrackNotFoundError:
        return json.dumps({"error": f"Issue '{issue_id}' not found"})
    except YouTrackError as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def list_projects() -> str:
    """List all accessible YouTrack projects.

    Returns:
        JSON array of projects with id, shortName, name, and description.
    """
    ctx = mcp.get_context()
    client: YouTrackClient = ctx.request_context.lifespan_context["client"]

    try:
        projects = await client.list_projects()

        result = {
            "count": len(projects),
            "projects": [format_project(p) for p in projects if not p.archived],
        }

        return json.dumps(result, indent=2)

    except YouTrackError as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def get_project_fields(project: str) -> str:
    """Get custom fields configured for a YouTrack project.

    This is useful for understanding what fields are available when creating
    or updating issues in a specific project.

    Args:
        project: Project short name (e.g., 'OPS').

    Returns:
        JSON array of custom field definitions with possible values.
    """
    ctx = mcp.get_context()
    client: YouTrackClient = ctx.request_context.lifespan_context["client"]

    try:
        fields = await client.get_project_custom_fields(project)

        # Simplify the field data for readability
        simplified: list[dict[str, Any]] = []
        for field in fields:
            field_info: dict[str, Any] = {
                "id": field.get("id"),
            }

            # Extract field name from nested object
            if "field" in field and field["field"]:
                field_info["name"] = field["field"].get("name")

            if "emptyFieldText" in field:
                field_info["emptyFieldText"] = field["emptyFieldText"]

            if "canBeEmpty" in field:
                field_info["required"] = not field["canBeEmpty"]

            # Extract possible values from bundle
            if "bundle" in field and field["bundle"]:
                bundle = field["bundle"]
                if "values" in bundle and bundle["values"]:
                    field_info["values"] = [
                        {"name": v.get("name"), "description": v.get("description")}
                        for v in bundle["values"]
                    ]

            simplified.append(field_info)

        return json.dumps(
            {"project": project, "fields": simplified},
            indent=2,
        )

    except YouTrackNotFoundError:
        return json.dumps({"error": f"Project '{project}' not found"})
    except YouTrackError as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def add_comment(issue_id: str, text: str) -> str:
    """Add a comment to an issue.

    Args:
        issue_id: The issue ID to comment on (e.g., 'OPS-123').
        text: Comment text (supports markdown).

    Returns:
        JSON object with the created comment details.
    """
    ctx = mcp.get_context()
    client: YouTrackClient = ctx.request_context.lifespan_context["client"]

    try:
        comment = await client.add_comment(issue_id, text)

        result = format_comment(comment)
        result["_created"] = True
        result["issue_id"] = issue_id

        return json.dumps(result, indent=2, default=str)

    except YouTrackNotFoundError:
        return json.dumps({"error": f"Issue '{issue_id}' not found"})
    except YouTrackError as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def list_comments(issue_id: str) -> str:
    """Get all comments on an issue.

    Args:
        issue_id: The issue ID to get comments for (e.g., 'OPS-123').

    Returns:
        JSON array of comments with author, text, and timestamps.
    """
    ctx = mcp.get_context()
    client: YouTrackClient = ctx.request_context.lifespan_context["client"]

    try:
        comments = await client.list_comments(issue_id)

        result = {
            "issue_id": issue_id,
            "count": len(comments),
            "comments": [format_comment(c) for c in comments],
        }

        return json.dumps(result, indent=2, default=str)

    except YouTrackNotFoundError:
        return json.dumps({"error": f"Issue '{issue_id}' not found"})
    except YouTrackError as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def list_link_types() -> str:
    """Get available issue link types.

    Returns:
        JSON array of link types with their directional names.
        Common types: Depend (depends on/is required for), Duplicate, Relate, Subtask.
    """
    ctx = mcp.get_context()
    client: YouTrackClient = ctx.request_context.lifespan_context["client"]

    try:
        link_types = await client.list_link_types()

        result = {
            "count": len(link_types),
            "link_types": [
                {
                    "name": lt.name,
                    "sourceToTarget": lt.source_to_target,
                    "targetToSource": lt.target_to_source,
                    "directed": lt.directed,
                }
                for lt in link_types
            ],
        }

        return json.dumps(result, indent=2)

    except YouTrackError as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def list_issue_links(issue_id: str) -> str:
    """Get all links for an issue.

    Args:
        issue_id: The issue ID to get links for (e.g., 'OPS-123').

    Returns:
        JSON object with linked issues grouped by link type and direction.
    """
    ctx = mcp.get_context()
    client: YouTrackClient = ctx.request_context.lifespan_context["client"]

    try:
        links = await client.list_issue_links(issue_id)

        formatted_links = []
        for link in links:
            link_info: dict[str, Any] = {
                "id": link.id,
                "direction": link.direction,
            }
            if link.link_type:
                link_info["linkType"] = link.link_type.name
                link_info["linkLabel"] = (
                    link.link_type.source_to_target
                    if link.direction == "OUTWARD"
                    else link.link_type.target_to_source
                )

            link_info["issues"] = [
                {"id": issue.id_readable or issue.id, "summary": issue.summary}
                for issue in link.issues
            ]
            formatted_links.append(link_info)

        result = {
            "issue_id": issue_id,
            "count": len(formatted_links),
            "links": formatted_links,
        }

        return json.dumps(result, indent=2, default=str)

    except YouTrackNotFoundError:
        return json.dumps({"error": f"Issue '{issue_id}' not found"})
    except YouTrackError as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def add_issue_link(
    issue_id: str,
    target_issue_id: str,
    link_type: str = "Depend",
) -> str:
    """Add a dependency or other link between two issues.

    Args:
        issue_id: Source issue ID (e.g., 'OPS-123').
        target_issue_id: Target issue ID to link to (e.g., 'OPS-456').
        link_type: Link type name (default 'Depend'). Use list_link_types to see options.

    Returns:
        JSON object confirming the link was added.

    Examples:
        - add_issue_link("OPS-123", "OPS-456", "Depend") - OPS-123 depends on OPS-456
        - add_issue_link("OPS-123", "OPS-42", "Duplicate") - OPS-123 duplicates OPS-42
    """
    ctx = mcp.get_context()
    client: YouTrackClient = ctx.request_context.lifespan_context["client"]

    try:
        await client.add_issue_link(issue_id, target_issue_id, link_type)

        return json.dumps({
            "success": True,
            "message": f"Added '{link_type}' link: {issue_id} -> {target_issue_id}",
            "issue_id": issue_id,
            "target_issue_id": target_issue_id,
            "link_type": link_type,
        }, indent=2)

    except YouTrackNotFoundError as e:
        return json.dumps({"error": str(e)})
    except YouTrackError as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def remove_issue_link(
    issue_id: str,
    target_issue_id: str,
    link_type: str = "Depend",
) -> str:
    """Remove a link between two issues.

    Args:
        issue_id: Source issue ID (e.g., 'OPS-123').
        target_issue_id: Target issue ID to unlink (e.g., 'OPS-456').
        link_type: Link type name (default 'Depend').

    Returns:
        JSON object confirming the link was removed.
    """
    ctx = mcp.get_context()
    client: YouTrackClient = ctx.request_context.lifespan_context["client"]

    try:
        await client.remove_issue_link(issue_id, target_issue_id, link_type)

        return json.dumps({
            "success": True,
            "message": f"Removed '{link_type}' link: {issue_id} -> {target_issue_id}",
            "issue_id": issue_id,
            "target_issue_id": target_issue_id,
            "link_type": link_type,
        }, indent=2)

    except YouTrackNotFoundError as e:
        return json.dumps({"error": str(e)})
    except YouTrackError as e:
        return json.dumps({"error": str(e)})


def run_server() -> None:
    """Run the MCP server."""
    mcp.run()
