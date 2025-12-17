"""Pytest fixtures for mcp_youtrack tests."""

from __future__ import annotations

from typing import Any

import pytest

from mcp_youtrack.config import YouTrackConfig


@pytest.fixture
def config() -> YouTrackConfig:
    """Create a test configuration."""
    return YouTrackConfig(
        url="https://youtrack.example.com",
        token="test-token-123",
        default_project="TEST",
        timeout=30,
    )


@pytest.fixture
def sample_issue_data() -> dict[str, Any]:
    """Sample issue response data from YouTrack API."""
    return {
        "id": "2-123",
        "idReadable": "TEST-123",
        "summary": "Test issue summary",
        "description": "This is a test issue description",
        "created": 1700000000000,
        "updated": 1700001000000,
        "resolved": None,
        "project": {
            "id": "0-1",
            "name": "Test Project",
            "shortName": "TEST",
        },
        "reporter": {
            "id": "1-1",
            "login": "testuser",
            "name": "Test User",
            "email": "test@example.com",
        },
        "updater": {
            "id": "1-1",
            "login": "testuser",
            "name": "Test User",
        },
        "customFields": [
            {
                "id": "cf-1",
                "name": "State",
                "value": {"id": "state-1", "name": "Open"},
            },
            {
                "id": "cf-2",
                "name": "Priority",
                "value": {"id": "priority-1", "name": "Normal"},
            },
            {
                "id": "cf-3",
                "name": "Type",
                "value": {"id": "type-1", "name": "Bug"},
            },
        ],
        "commentsCount": 0,
        "votes": 0,
    }


@pytest.fixture
def sample_project_data() -> dict[str, Any]:
    """Sample project response data from YouTrack API."""
    return {
        "id": "0-1",
        "name": "Test Project",
        "shortName": "TEST",
        "description": "A test project for unit tests",
        "archived": False,
    }


@pytest.fixture
def sample_comment_data() -> dict[str, Any]:
    """Sample comment response data from YouTrack API."""
    return {
        "id": "4-1",
        "text": "This is a test comment",
        "author": {
            "id": "1-1",
            "login": "testuser",
            "name": "Test User",
        },
        "created": 1700002000000,
        "updated": None,
    }


@pytest.fixture
def sample_project_fields_data() -> list[dict[str, Any]]:
    """Sample project custom fields response data."""
    return [
        {
            "id": "cf-1",
            "field": {"id": "f-1", "name": "State"},
            "emptyFieldText": "No state",
            "canBeEmpty": False,
            "bundle": {
                "id": "bundle-1",
                "values": [
                    {"id": "v-1", "name": "Open", "description": "Issue is open"},
                    {"id": "v-2", "name": "In Progress", "description": "Being worked on"},
                    {"id": "v-3", "name": "Done", "description": "Issue is completed"},
                ],
            },
        },
        {
            "id": "cf-2",
            "field": {"id": "f-2", "name": "Priority"},
            "emptyFieldText": "No priority",
            "canBeEmpty": True,
            "bundle": {
                "id": "bundle-2",
                "values": [
                    {"id": "v-4", "name": "Low", "description": None},
                    {"id": "v-5", "name": "Normal", "description": None},
                    {"id": "v-6", "name": "High", "description": None},
                    {"id": "v-7", "name": "Critical", "description": None},
                ],
            },
        },
    ]
