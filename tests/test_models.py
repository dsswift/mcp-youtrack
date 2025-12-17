"""Tests for Pydantic models."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from mcp_youtrack.models import (
    Comment,
    CustomField,
    CustomFieldValue,
    Issue,
    IssueCreate,
    IssueUpdate,
    Project,
    User,
)


class TestUser:
    """Tests for User model."""

    def test_parse_user(self) -> None:
        """Test parsing a user from API response."""
        data = {
            "id": "1-1",
            "login": "testuser",
            "name": "Test User",
            "email": "test@example.com",
        }
        user = User.model_validate(data)
        assert user.id == "1-1"
        assert user.login == "testuser"
        assert user.name == "Test User"
        assert user.email == "test@example.com"

    def test_parse_user_minimal(self) -> None:
        """Test parsing a user with minimal data."""
        data = {"id": "1-1"}
        user = User.model_validate(data)
        assert user.id == "1-1"
        assert user.login is None
        assert user.name is None


class TestProject:
    """Tests for Project model."""

    def test_parse_project(self, sample_project_data: dict[str, Any]) -> None:
        """Test parsing a project from API response."""
        project = Project.model_validate(sample_project_data)
        assert project.id == "0-1"
        assert project.short_name == "TEST"
        assert project.name == "Test Project"
        assert project.description == "A test project for unit tests"
        assert project.archived is False


class TestCustomField:
    """Tests for CustomField model."""

    def test_parse_single_value(self) -> None:
        """Test parsing a custom field with single value."""
        data = {
            "id": "cf-1",
            "name": "State",
            "value": {"id": "v-1", "name": "Open"},
        }
        field = CustomField.model_validate(data)
        assert field.name == "State"
        assert isinstance(field.value, CustomFieldValue)
        assert field.value.name == "Open"

    def test_parse_multi_value(self) -> None:
        """Test parsing a custom field with multiple values."""
        data = {
            "id": "cf-1",
            "name": "Tags",
            "value": [
                {"id": "t-1", "name": "frontend"},
                {"id": "t-2", "name": "urgent"},
            ],
        }
        field = CustomField.model_validate(data)
        assert field.name == "Tags"
        assert isinstance(field.value, list)
        assert len(field.value) == 2
        assert field.value[0].name == "frontend"
        assert field.value[1].name == "urgent"

    def test_parse_null_value(self) -> None:
        """Test parsing a custom field with null value."""
        data = {"id": "cf-1", "name": "Assignee", "value": None}
        field = CustomField.model_validate(data)
        assert field.value is None


class TestComment:
    """Tests for Comment model."""

    def test_parse_comment(self, sample_comment_data: dict[str, Any]) -> None:
        """Test parsing a comment from API response."""
        comment = Comment.model_validate(sample_comment_data)
        assert comment.id == "4-1"
        assert comment.text == "This is a test comment"
        assert comment.author is not None
        assert comment.author.name == "Test User"
        assert comment.created is not None
        assert isinstance(comment.created, datetime)


class TestIssue:
    """Tests for Issue model."""

    def test_parse_issue(self, sample_issue_data: dict[str, Any]) -> None:
        """Test parsing an issue from API response."""
        issue = Issue.model_validate(sample_issue_data)
        assert issue.id == "2-123"
        assert issue.id_readable == "TEST-123"
        assert issue.summary == "Test issue summary"
        assert issue.description == "This is a test issue description"
        assert issue.project is not None
        assert issue.project.short_name == "TEST"
        assert issue.reporter is not None
        assert issue.reporter.login == "testuser"
        assert len(issue.custom_fields) == 3

    def test_parse_timestamps(self, sample_issue_data: dict[str, Any]) -> None:
        """Test timestamp parsing (milliseconds to datetime)."""
        issue = Issue.model_validate(sample_issue_data)
        assert issue.created is not None
        assert isinstance(issue.created, datetime)
        assert issue.updated is not None
        assert issue.resolved is None

    def test_get_field_value(self, sample_issue_data: dict[str, Any]) -> None:
        """Test getting custom field value by name."""
        issue = Issue.model_validate(sample_issue_data)
        assert issue.get_field_value("State") == "Open"
        assert issue.get_field_value("Type") == "Bug"
        assert issue.get_field_value("NonExistent") is None


class TestIssueCreate:
    """Tests for IssueCreate model."""

    def test_to_api_payload(self) -> None:
        """Test converting to API payload."""
        create = IssueCreate(
            project="proj-123",
            summary="New issue",
            description="Issue description",
        )
        payload = create.to_api_payload()
        assert payload == {
            "project": {"id": "proj-123"},
            "summary": "New issue",
            "description": "Issue description",
        }

    def test_to_api_payload_no_description(self) -> None:
        """Test payload without description."""
        create = IssueCreate(
            project="proj-123",
            summary="New issue",
        )
        payload = create.to_api_payload()
        assert "description" not in payload


class TestIssueUpdate:
    """Tests for IssueUpdate model."""

    def test_to_api_payload(self) -> None:
        """Test converting to API payload."""
        update = IssueUpdate(
            summary="Updated summary",
            description="Updated description",
        )
        payload = update.to_api_payload()
        assert payload == {
            "summary": "Updated summary",
            "description": "Updated description",
        }

    def test_to_api_payload_partial(self) -> None:
        """Test payload with only summary."""
        update = IssueUpdate(summary="Updated summary")
        payload = update.to_api_payload()
        assert payload == {"summary": "Updated summary"}

    def test_to_api_payload_empty(self) -> None:
        """Test empty payload."""
        update = IssueUpdate()
        payload = update.to_api_payload()
        assert payload == {}
