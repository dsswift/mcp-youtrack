"""Configuration module for YouTrack MCP Server."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass
class YouTrackConfig:
    """Configuration for YouTrack API connection."""

    url: str
    token: str
    default_project: str | None = None
    timeout: int = 30
    verify_ssl: bool = True

    @property
    def api_url(self) -> str:
        """Get the API base URL."""
        return f"{self.url.rstrip('/')}/api"

    @property
    def auth_header(self) -> dict[str, str]:
        """Get the authorization header."""
        return {"Authorization": f"Bearer {self.token}"}


def load_config() -> YouTrackConfig:
    """Load configuration from environment variables.

    Returns:
        YouTrackConfig: Validated configuration object.

    Raises:
        SystemExit: If required environment variables are missing.
    """
    load_dotenv()

    url = os.getenv("YOUTRACK_URL")
    token = os.getenv("YOUTRACK_TOKEN")

    errors: list[str] = []

    if not url:
        errors.append("YOUTRACK_URL environment variable is required")
    if not token:
        errors.append("YOUTRACK_TOKEN environment variable is required")

    if errors or not url or not token:
        for error in errors:
            print(f"Configuration error: {error}", file=sys.stderr)
        print(
            "\nSee .env.sample for required configuration.",
            file=sys.stderr,
        )
        sys.exit(1)

    timeout_str = os.getenv("YOUTRACK_TIMEOUT", "30")
    try:
        timeout = int(timeout_str)
    except ValueError:
        print(
            f"Warning: Invalid YOUTRACK_TIMEOUT value '{timeout_str}', using default 30",
            file=sys.stderr,
        )
        timeout = 30

    # SSL verification - default True, set to "false" to disable
    verify_ssl_str = os.getenv("YOUTRACK_VERIFY_SSL", "true").lower()
    verify_ssl = verify_ssl_str not in ("false", "0", "no")

    return YouTrackConfig(
        url=url,
        token=token,
        default_project=os.getenv("YOUTRACK_DEFAULT_PROJECT"),
        timeout=timeout,
        verify_ssl=verify_ssl,
    )
