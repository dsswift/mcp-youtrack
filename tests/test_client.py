"""Tests for YouTrack HTTP client."""

from __future__ import annotations

import re
from typing import Any

import pytest
from pytest_httpx import HTTPXMock

from mcp_youtrack.client import (
    YouTrackAuthError,
    YouTrackClient,
    YouTrackError,
    YouTrackNotFoundError,
)
from mcp_youtrack.config import YouTrackConfig


class TestYouTrackClient:
    """Tests for YouTrackClient."""

    @pytest.fixture
    def client(self, config: YouTrackConfig) -> YouTrackClient:
        """Create a test client instance."""
        return YouTrackClient(config)

    async def test_list_issues(
        self,
        client: YouTrackClient,
        httpx_mock: HTTPXMock,
        sample_issue_data: dict[str, Any],
    ) -> None:
        """Test listing issues."""
        httpx_mock.add_response(
            url=re.compile(r".*/api/issues.*"),
            json=[sample_issue_data],
        )

        async with client:
            issues = await client.list_issues()

        assert len(issues) == 1
        assert issues[0].id_readable == "TEST-123"

    async def test_list_issues_with_query(
        self,
        client: YouTrackClient,
        httpx_mock: HTTPXMock,
        sample_issue_data: dict[str, Any],
    ) -> None:
        """Test listing issues with project filter."""
        httpx_mock.add_response(
            url=re.compile(r".*/api/issues.*"),
            json=[sample_issue_data],
        )

        async with client:
            issues = await client.list_issues(project="TEST", query="#Open")

        assert len(issues) == 1
        # Verify the query was constructed correctly
        request = httpx_mock.get_request()
        assert request is not None
        assert "project" in str(request.url)

    async def test_get_issue(
        self,
        client: YouTrackClient,
        httpx_mock: HTTPXMock,
        sample_issue_data: dict[str, Any],
    ) -> None:
        """Test getting a single issue."""
        httpx_mock.add_response(
            url=re.compile(r".*/api/issues/TEST-123.*"),
            json=sample_issue_data,
        )

        async with client:
            issue = await client.get_issue("TEST-123")

        assert issue.id_readable == "TEST-123"
        assert issue.summary == "Test issue summary"

    async def test_get_issue_not_found(
        self,
        client: YouTrackClient,
        httpx_mock: HTTPXMock,
    ) -> None:
        """Test 404 error handling."""
        httpx_mock.add_response(
            url=re.compile(r".*/api/issues/TEST-999.*"),
            status_code=404,
            json={"error": "Issue not found"},
        )

        async with client:
            with pytest.raises(YouTrackNotFoundError):
                await client.get_issue("TEST-999")

    async def test_create_issue(
        self,
        client: YouTrackClient,
        httpx_mock: HTTPXMock,
        sample_issue_data: dict[str, Any],
    ) -> None:
        """Test creating an issue."""
        httpx_mock.add_response(
            url=re.compile(r".*/api/issues.*"),
            method="POST",
            json=sample_issue_data,
            status_code=200,
        )

        async with client:
            issue = await client.create_issue(
                project_id="0-1",
                summary="New issue",
                description="Description",
            )

        assert issue.id_readable == "TEST-123"

    async def test_update_issue(
        self,
        client: YouTrackClient,
        httpx_mock: HTTPXMock,
        sample_issue_data: dict[str, Any],
    ) -> None:
        """Test updating an issue."""
        httpx_mock.add_response(
            url=re.compile(r".*/api/issues/TEST-123.*"),
            method="POST",
            json=sample_issue_data,
        )

        async with client:
            issue = await client.update_issue(
                issue_id="TEST-123",
                summary="Updated summary",
            )

        assert issue.id_readable == "TEST-123"

    async def test_delete_issue(
        self,
        client: YouTrackClient,
        httpx_mock: HTTPXMock,
    ) -> None:
        """Test deleting an issue."""
        httpx_mock.add_response(
            url=re.compile(r".*/api/issues/TEST-123"),
            method="DELETE",
            status_code=200,
        )

        async with client:
            result = await client.delete_issue("TEST-123")

        assert result is True

    async def test_list_projects(
        self,
        client: YouTrackClient,
        httpx_mock: HTTPXMock,
        sample_project_data: dict[str, Any],
    ) -> None:
        """Test listing projects."""
        httpx_mock.add_response(
            url=re.compile(r".*/api/admin/projects.*"),
            json=[sample_project_data],
        )

        async with client:
            projects = await client.list_projects()

        assert len(projects) == 1
        assert projects[0].short_name == "TEST"

    async def test_get_project(
        self,
        client: YouTrackClient,
        httpx_mock: HTTPXMock,
        sample_project_data: dict[str, Any],
    ) -> None:
        """Test getting a project."""
        httpx_mock.add_response(
            url=re.compile(r".*/api/admin/projects/TEST.*"),
            json=sample_project_data,
        )

        async with client:
            project = await client.get_project("TEST")

        assert project.short_name == "TEST"
        assert project.name == "Test Project"

    async def test_get_project_custom_fields(
        self,
        client: YouTrackClient,
        httpx_mock: HTTPXMock,
        sample_project_fields_data: list[dict[str, Any]],
    ) -> None:
        """Test getting project custom fields."""
        httpx_mock.add_response(
            url=re.compile(r".*/api/admin/projects/TEST/customFields.*"),
            json=sample_project_fields_data,
        )

        async with client:
            fields = await client.get_project_custom_fields("TEST")

        assert len(fields) == 2
        assert fields[0]["field"]["name"] == "State"

    async def test_execute_command(
        self,
        client: YouTrackClient,
        httpx_mock: HTTPXMock,
    ) -> None:
        """Test executing a command."""
        httpx_mock.add_response(
            url=re.compile(r".*/api/commands"),
            method="POST",
            status_code=200,
        )

        async with client:
            await client.execute_command("TEST-123", "State: Done")

        request = httpx_mock.get_request()
        assert request is not None

    async def test_add_comment(
        self,
        client: YouTrackClient,
        httpx_mock: HTTPXMock,
        sample_comment_data: dict[str, Any],
    ) -> None:
        """Test adding a comment."""
        httpx_mock.add_response(
            url=re.compile(r".*/api/issues/TEST-123/comments.*"),
            method="POST",
            json=sample_comment_data,
        )

        async with client:
            comment = await client.add_comment("TEST-123", "Test comment")

        assert comment.text == "This is a test comment"

    async def test_list_comments(
        self,
        client: YouTrackClient,
        httpx_mock: HTTPXMock,
        sample_comment_data: dict[str, Any],
    ) -> None:
        """Test listing comments."""
        httpx_mock.add_response(
            url=re.compile(r".*/api/issues/TEST-123/comments.*"),
            json=[sample_comment_data],
        )

        async with client:
            comments = await client.list_comments("TEST-123")

        assert len(comments) == 1
        assert comments[0].text == "This is a test comment"

    async def test_delete_comment(
        self,
        client: YouTrackClient,
        httpx_mock: HTTPXMock,
    ) -> None:
        """Test deleting a comment."""
        httpx_mock.add_response(
            url=re.compile(r".*/api/issues/TEST-123/comments/1-1"),
            method="DELETE",
            status_code=200,
        )

        async with client:
            result = await client.delete_comment("TEST-123", "1-1")

        assert result is True

    async def test_delete_comment_not_found(
        self,
        client: YouTrackClient,
        httpx_mock: HTTPXMock,
    ) -> None:
        """Test 404 error when deleting a non-existent comment."""
        httpx_mock.add_response(
            url=re.compile(r".*/api/issues/TEST-123/comments/invalid-id"),
            method="DELETE",
            status_code=404,
            json={"error": "Comment not found"},
        )

        async with client:
            with pytest.raises(YouTrackNotFoundError):
                await client.delete_comment("TEST-123", "invalid-id")

    async def test_auth_error(
        self,
        client: YouTrackClient,
        httpx_mock: HTTPXMock,
    ) -> None:
        """Test 401 authentication error."""
        httpx_mock.add_response(
            url=re.compile(r".*/api/issues.*"),
            status_code=401,
            json={"error": "Unauthorized"},
        )

        async with client:
            with pytest.raises(YouTrackAuthError) as exc_info:
                await client.list_issues()

        assert "Authentication failed" in str(exc_info.value)

    async def test_permission_error(
        self,
        client: YouTrackClient,
        httpx_mock: HTTPXMock,
    ) -> None:
        """Test 403 permission error."""
        httpx_mock.add_response(
            url=re.compile(r".*/api/issues.*"),
            status_code=403,
            json={"error": "Forbidden"},
        )

        async with client:
            with pytest.raises(YouTrackAuthError) as exc_info:
                await client.list_issues()

        assert "Permission denied" in str(exc_info.value)

    async def test_server_error(
        self,
        client: YouTrackClient,
        httpx_mock: HTTPXMock,
    ) -> None:
        """Test 500 server error."""
        httpx_mock.add_response(
            url=re.compile(r".*/api/issues.*"),
            status_code=500,
            text="Internal Server Error",
        )

        async with client:
            with pytest.raises(YouTrackError) as exc_info:
                await client.list_issues()

        assert "API error (500)" in str(exc_info.value)

    async def test_client_not_initialized_error(
        self,
        client: YouTrackClient,
    ) -> None:
        """Test error when client used outside context manager."""
        with pytest.raises(RuntimeError) as exc_info:
            _ = client.client

        assert "Client not initialized" in str(exc_info.value)
