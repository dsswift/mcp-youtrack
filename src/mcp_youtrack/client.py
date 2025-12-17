"""YouTrack REST API client."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from .config import YouTrackConfig
from .models import Comment, Issue, IssueCreate, IssueLink, IssueLinkType, IssueUpdate, Project

logger = logging.getLogger(__name__)


class YouTrackError(Exception):
    """Base exception for YouTrack API errors."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class YouTrackAuthError(YouTrackError):
    """Authentication/authorization error."""

    pass


class YouTrackNotFoundError(YouTrackError):
    """Resource not found error."""

    pass


# Default fields to request from the API
ISSUE_FIELDS = (
    "id,idReadable,summary,description,created,updated,resolved,"
    "project(id,name,shortName),"
    "reporter(id,login,name,email),"
    "updater(id,login,name),"
    "customFields(id,name,value(id,name,login,presentation)),"
    "commentsCount,votes"
)

PROJECT_FIELDS = "id,name,shortName,description,archived"

PROJECT_CUSTOM_FIELDS = (
    "id,field(id,name),emptyFieldText,canBeEmpty,"
    "bundle(id,values(id,name,description))"
)

COMMENT_FIELDS = "id,text,author(id,login,name),created,updated"


class YouTrackClient:
    """Async client for YouTrack REST API."""

    def __init__(self, config: YouTrackConfig) -> None:
        """Initialize the client with configuration."""
        self.config = config
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> YouTrackClient:
        """Enter async context."""
        self._client = httpx.AsyncClient(
            base_url=self.config.api_url,
            headers={
                **self.config.auth_header,
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            timeout=self.config.timeout,
            verify=self.config.verify_ssl,
        )
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Exit async context."""
        if self._client:
            await self._client.aclose()
            self._client = None

    @property
    def client(self) -> httpx.AsyncClient:
        """Get the HTTP client, ensuring it's initialized."""
        if self._client is None:
            raise RuntimeError(
                "Client not initialized. Use 'async with YouTrackClient(config)' context."
            )
        return self._client

    def _handle_error(self, response: httpx.Response) -> None:
        """Handle HTTP error responses."""
        status = response.status_code

        try:
            error_data = response.json()
            message = error_data.get("error_description") or error_data.get("error", str(status))
        except Exception:
            message = response.text or f"HTTP {status}"

        if status == 401:
            raise YouTrackAuthError(
                "Authentication failed. Check your YOUTRACK_TOKEN.",
                status_code=status,
            )
        elif status == 403:
            raise YouTrackAuthError(
                f"Permission denied: {message}",
                status_code=status,
            )
        elif status == 404:
            raise YouTrackNotFoundError(
                f"Resource not found: {message}",
                status_code=status,
            )
        else:
            raise YouTrackError(
                f"API error ({status}): {message}",
                status_code=status,
            )

    async def list_issues(
        self,
        project: str | None = None,
        query: str | None = None,
        limit: int = 25,
        skip: int = 0,
    ) -> list[Issue]:
        """Search and list issues.

        Args:
            project: Project short name to filter by.
            query: YouTrack search query.
            limit: Maximum number of results (default 25).
            skip: Number of results to skip for pagination.

        Returns:
            List of matching issues.
        """
        # Build query string
        query_parts: list[str] = []
        if project:
            query_parts.append(f"project: {project}")
        if query:
            query_parts.append(query)

        full_query = " ".join(query_parts) if query_parts else None

        params: dict[str, Any] = {
            "fields": ISSUE_FIELDS,
            "$top": limit,
            "$skip": skip,
        }
        if full_query:
            params["query"] = full_query

        logger.debug("Listing issues with params: %s", params)
        response = await self.client.get("/issues", params=params)

        if not response.is_success:
            self._handle_error(response)

        data = response.json()
        return [Issue.model_validate(item) for item in data]

    async def get_issue(self, issue_id: str) -> Issue:
        """Get a single issue by ID.

        Args:
            issue_id: Issue ID (readable like 'PROJECT-123' or database ID).

        Returns:
            The issue details.

        Raises:
            YouTrackNotFoundError: If the issue doesn't exist.
        """
        logger.debug("Getting issue: %s", issue_id)
        response = await self.client.get(
            f"/issues/{issue_id}",
            params={"fields": ISSUE_FIELDS},
        )

        if not response.is_success:
            self._handle_error(response)

        return Issue.model_validate(response.json())

    async def create_issue(
        self,
        project_id: str,
        summary: str,
        description: str | None = None,
    ) -> Issue:
        """Create a new issue.

        Args:
            project_id: Project ID (database ID, not short name).
            summary: Issue summary/title.
            description: Issue description (optional).

        Returns:
            The created issue.
        """
        create_data = IssueCreate(
            project=project_id,
            summary=summary,
            description=description,
        )

        logger.debug("Creating issue in project %s: %s", project_id, summary)
        response = await self.client.post(
            "/issues",
            json=create_data.to_api_payload(),
            params={"fields": ISSUE_FIELDS},
        )

        if not response.is_success:
            self._handle_error(response)

        return Issue.model_validate(response.json())

    async def update_issue(
        self,
        issue_id: str,
        summary: str | None = None,
        description: str | None = None,
    ) -> Issue:
        """Update an existing issue.

        Args:
            issue_id: Issue ID to update.
            summary: New summary (optional).
            description: New description (optional).

        Returns:
            The updated issue.
        """
        update_data = IssueUpdate(
            summary=summary,
            description=description,
        )

        payload = update_data.to_api_payload()
        if not payload:
            # No changes requested, just return the current issue
            return await self.get_issue(issue_id)

        logger.debug("Updating issue %s with: %s", issue_id, payload)
        response = await self.client.post(
            f"/issues/{issue_id}",
            json=payload,
            params={"fields": ISSUE_FIELDS},
        )

        if not response.is_success:
            self._handle_error(response)

        return Issue.model_validate(response.json())

    async def delete_issue(self, issue_id: str) -> bool:
        """Delete an issue.

        Args:
            issue_id: Issue ID to delete.

        Returns:
            True if deleted successfully.

        Raises:
            YouTrackNotFoundError: If the issue doesn't exist.
        """
        logger.debug("Deleting issue: %s", issue_id)
        response = await self.client.delete(f"/issues/{issue_id}")

        if not response.is_success:
            self._handle_error(response)

        return True

    async def list_projects(self, limit: int = 100, skip: int = 0) -> list[Project]:
        """List all accessible projects.

        Args:
            limit: Maximum number of projects to return.
            skip: Number of projects to skip for pagination.

        Returns:
            List of projects.
        """
        logger.debug("Listing projects")
        response = await self.client.get(
            "/admin/projects",
            params={
                "fields": PROJECT_FIELDS,
                "$top": limit,
                "$skip": skip,
            },
        )

        if not response.is_success:
            self._handle_error(response)

        data = response.json()
        return [Project.model_validate(item) for item in data]

    async def get_project(self, project_id: str) -> Project:
        """Get a project by ID or short name.

        Args:
            project_id: Project ID or short name.

        Returns:
            The project details.
        """
        logger.debug("Getting project: %s", project_id)
        response = await self.client.get(
            f"/admin/projects/{project_id}",
            params={"fields": PROJECT_FIELDS},
        )

        if not response.is_success:
            self._handle_error(response)

        return Project.model_validate(response.json())

    async def get_project_custom_fields(self, project_id: str) -> list[dict[str, Any]]:
        """Get custom fields configured for a project.

        Args:
            project_id: Project ID or short name.

        Returns:
            List of custom field definitions with possible values.
        """
        logger.debug("Getting custom fields for project: %s", project_id)
        response = await self.client.get(
            f"/admin/projects/{project_id}/customFields",
            params={"fields": PROJECT_CUSTOM_FIELDS},
        )

        if not response.is_success:
            self._handle_error(response)

        result: list[dict[str, Any]] = response.json()
        return result

    async def execute_command(
        self,
        issue_id: str,
        command: str,
        comment: str | None = None,
    ) -> None:
        """Execute a YouTrack command on an issue.

        This is useful for changing state, assignee, and other fields
        that are managed via commands rather than direct field updates.

        Args:
            issue_id: Issue ID to run command on.
            command: Command text (e.g., "State: Open", "Assignee: john").
            comment: Optional comment to add with the command.
        """
        payload: dict[str, Any] = {
            "query": command,
            "issues": [{"idReadable": issue_id}],
        }
        if comment:
            payload["comment"] = comment

        logger.debug("Executing command on %s: %s", issue_id, command)
        response = await self.client.post("/commands", json=payload)

        if not response.is_success:
            self._handle_error(response)

    async def add_comment(self, issue_id: str, text: str) -> Comment:
        """Add a comment to an issue.

        Args:
            issue_id: Issue ID to comment on.
            text: Comment text (supports markdown).

        Returns:
            The created comment.
        """
        logger.debug("Adding comment to %s", issue_id)
        response = await self.client.post(
            f"/issues/{issue_id}/comments",
            json={"text": text},
            params={"fields": COMMENT_FIELDS},
        )

        if not response.is_success:
            self._handle_error(response)

        return Comment.model_validate(response.json())

    async def list_comments(self, issue_id: str) -> list[Comment]:
        """Get all comments on an issue.

        Args:
            issue_id: Issue ID to get comments for.

        Returns:
            List of comments.
        """
        logger.debug("Listing comments for %s", issue_id)
        response = await self.client.get(
            f"/issues/{issue_id}/comments",
            params={"fields": COMMENT_FIELDS},
        )

        if not response.is_success:
            self._handle_error(response)

        data = response.json()
        return [Comment.model_validate(item) for item in data]

    async def delete_comment(self, issue_id: str, comment_id: str) -> bool:
        """Delete a comment from an issue.

        Args:
            issue_id: Issue ID the comment belongs to.
            comment_id: Comment ID to delete.

        Returns:
            True if deleted successfully.

        Raises:
            YouTrackNotFoundError: If the issue or comment doesn't exist.
        """
        logger.debug("Deleting comment %s from issue %s", comment_id, issue_id)
        response = await self.client.delete(f"/issues/{issue_id}/comments/{comment_id}")

        if not response.is_success:
            self._handle_error(response)

        return True

    async def list_link_types(self) -> list[IssueLinkType]:
        """Get all available issue link types.

        Returns:
            List of link types with their directional names.
        """
        logger.debug("Listing issue link types")
        response = await self.client.get(
            "/issueLinkTypes",
            params={"fields": "id,name,sourceToTarget,targetToSource,directed,aggregation"},
        )

        if not response.is_success:
            self._handle_error(response)

        data = response.json()
        return [IssueLinkType.model_validate(item) for item in data]

    async def list_issue_links(self, issue_id: str) -> list[IssueLink]:
        """Get all links for an issue.

        Args:
            issue_id: Issue ID to get links for.

        Returns:
            List of issue links with linked issues.
        """
        logger.debug("Listing links for issue %s", issue_id)
        response = await self.client.get(
            f"/issues/{issue_id}/links",
            params={
                "fields": "id,direction,linkType(id,name,sourceToTarget,targetToSource,directed),"
                          "issues(id,idReadable,summary)"
            },
        )

        if not response.is_success:
            self._handle_error(response)

        data = response.json()
        return [IssueLink.model_validate(item) for item in data]

    async def add_issue_link(
        self,
        issue_id: str,
        target_issue_id: str,
        link_type: str,
    ) -> None:
        """Add a link between two issues.

        Args:
            issue_id: Source issue ID (e.g., 'PROJECT-123').
            target_issue_id: Target issue ID to link to (e.g., 'PROJECT-456').
            link_type: Link type name (e.g., 'Depend', 'Duplicate', 'Relate', 'Subtask').

        Note:
            For 'Depend' type: issue_id "depends on" target_issue_id.
        """
        # First, get the link type ID
        link_types = await self.list_link_types()
        link_type_obj = next(
            (lt for lt in link_types if lt.name and lt.name.lower() == link_type.lower()),
            None
        )
        if not link_type_obj:
            available = [lt.name for lt in link_types if lt.name]
            raise YouTrackError(
                f"Unknown link type '{link_type}'. Available types: {', '.join(available)}"
            )

        # Use command API to add the link
        command = f"{link_type_obj.source_to_target} {target_issue_id}"

        logger.debug("Adding link from %s to %s: %s", issue_id, target_issue_id, command)
        await self.execute_command(issue_id, command)

    async def remove_issue_link(
        self,
        issue_id: str,
        target_issue_id: str,
        link_type: str,
    ) -> None:
        """Remove a link between two issues.

        Args:
            issue_id: Source issue ID (e.g., 'PROJECT-123').
            target_issue_id: Target issue ID to unlink (e.g., 'PROJECT-456').
            link_type: Link type name (e.g., 'Depend', 'Duplicate', 'Relate', 'Subtask').
        """
        # First, get the link type ID
        link_types = await self.list_link_types()
        link_type_obj = next(
            (lt for lt in link_types if lt.name and lt.name.lower() == link_type.lower()),
            None
        )
        if not link_type_obj:
            available = [lt.name for lt in link_types if lt.name]
            raise YouTrackError(
                f"Unknown link type '{link_type}'. Available types: {', '.join(available)}"
            )

        # Use command API with "remove" prefix to remove the link
        command = f"remove {link_type_obj.source_to_target} {target_issue_id}"

        logger.debug("Removing link from %s to %s: %s", issue_id, target_issue_id, command)
        await self.execute_command(issue_id, command)
