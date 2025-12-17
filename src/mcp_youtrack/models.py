"""Pydantic models for YouTrack API entities."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


class User(BaseModel):
    """YouTrack user entity."""

    id: str
    login: str | None = None
    name: str | None = None
    email: str | None = None


class Project(BaseModel):
    """YouTrack project entity."""

    id: str
    name: str | None = None
    short_name: str | None = Field(None, alias="shortName")
    description: str | None = None
    archived: bool = False


class CustomFieldValue(BaseModel):
    """Value of a custom field (can be various types)."""

    id: str | None = None
    name: str | None = None
    login: str | None = None  # For user fields
    presentation: str | None = None  # Formatted display value


class CustomField(BaseModel):
    """YouTrack custom field on an issue."""

    id: str | None = None
    name: str | None = None
    value: CustomFieldValue | list[CustomFieldValue] | str | int | float | None = None

    @field_validator("value", mode="before")
    @classmethod
    def parse_value(
        cls, v: Any
    ) -> CustomFieldValue | list[CustomFieldValue] | str | int | float | None:
        """Parse custom field value which can be various types."""
        if v is None:
            return None
        if isinstance(v, (str, int, float)):
            return v
        if isinstance(v, list):
            return [CustomFieldValue.model_validate(item) for item in v]
        if isinstance(v, dict):
            return CustomFieldValue.model_validate(v)
        # For any other type, try to convert to string
        return str(v)


class ProjectCustomField(BaseModel):
    """Custom field definition for a project."""

    id: str
    name: str | None = Field(None, alias="field")
    field_name: str | None = None
    empty_field_text: str | None = Field(None, alias="emptyFieldText")
    can_be_empty: bool | None = Field(None, alias="canBeEmpty")

    @field_validator("field_name", mode="before")
    @classmethod
    def extract_field_name(cls, v: Any, info: Any) -> str | None:
        """Extract field name from nested field object."""
        # The field object is in 'field' key of raw data
        if v is None and hasattr(info, "data"):
            field_data = info.data.get("field")
            if isinstance(field_data, dict):
                name_val = field_data.get("name")
                return str(name_val) if name_val is not None else None
        if v is not None:
            return str(v)
        return None


class Comment(BaseModel):
    """YouTrack comment entity."""

    id: str
    text: str | None = None
    author: User | None = None
    created: datetime | None = None
    updated: datetime | None = None

    @field_validator("created", "updated", mode="before")
    @classmethod
    def parse_timestamp(cls, v: Any) -> datetime | None:
        """Parse Unix timestamp (milliseconds) to datetime."""
        if v is None:
            return None
        if isinstance(v, int):
            return datetime.fromtimestamp(v / 1000)
        if isinstance(v, datetime):
            return v
        return None


class Issue(BaseModel):
    """YouTrack issue entity."""

    id: str
    id_readable: str | None = Field(None, alias="idReadable")
    summary: str | None = None
    description: str | None = None
    created: datetime | None = None
    updated: datetime | None = None
    resolved: datetime | None = None
    project: Project | None = None
    reporter: User | None = None
    updater: User | None = None
    custom_fields: list[CustomField] = Field(default_factory=list, alias="customFields")
    comments_count: int | None = Field(None, alias="commentsCount")
    votes: int | None = None

    @field_validator("created", "updated", "resolved", mode="before")
    @classmethod
    def parse_timestamp(cls, v: Any) -> datetime | None:
        """Parse Unix timestamp (milliseconds) to datetime."""
        if v is None:
            return None
        if isinstance(v, int):
            return datetime.fromtimestamp(v / 1000)
        if isinstance(v, datetime):
            return v
        return None

    def get_field_value(self, field_name: str) -> Any:
        """Get the value of a custom field by name."""
        for field in self.custom_fields:
            if field.name == field_name:
                if isinstance(field.value, CustomFieldValue):
                    return field.value.name or field.value.presentation
                return field.value
        return None


class IssueCreate(BaseModel):
    """Request model for creating an issue."""

    project_id: str = Field(..., alias="project")
    summary: str
    description: str | None = None

    def to_api_payload(self) -> dict[str, Any]:
        """Convert to YouTrack API payload format."""
        payload: dict[str, Any] = {
            "project": {"id": self.project_id},
            "summary": self.summary,
        }
        if self.description:
            payload["description"] = self.description
        return payload


class IssueUpdate(BaseModel):
    """Request model for updating an issue."""

    summary: str | None = None
    description: str | None = None

    def to_api_payload(self) -> dict[str, Any]:
        """Convert to YouTrack API payload format."""
        payload: dict[str, Any] = {}
        if self.summary is not None:
            payload["summary"] = self.summary
        if self.description is not None:
            payload["description"] = self.description
        return payload


class IssueSearchResult(BaseModel):
    """Result of an issue search operation."""

    issues: list[Issue]
    total: int | None = None
    query: str | None = None


class ProjectListResult(BaseModel):
    """Result of a project list operation."""

    projects: list[Project]
    total: int


class IssueLinkType(BaseModel):
    """YouTrack issue link type."""

    id: str | None = None
    name: str | None = None
    source_to_target: str | None = Field(None, alias="sourceToTarget")
    target_to_source: str | None = Field(None, alias="targetToSource")
    directed: bool = True
    aggregation: bool = False


class IssueLinkDirection(BaseModel):
    """Direction info for an issue link."""

    id: str | None = None
    name: str | None = None


class IssueLink(BaseModel):
    """YouTrack issue link entity."""

    id: str
    direction: str | None = None  # "OUTWARD", "INWARD", or "BOTH"
    link_type: IssueLinkType | None = Field(None, alias="linkType")
    issues: list[Issue] = Field(default_factory=list)
    trimmed_issues: list[Issue] = Field(default_factory=list, alias="trimmedIssues")
