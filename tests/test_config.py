"""Tests for configuration module."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from mcp_youtrack.config import YouTrackConfig, load_config


class TestYouTrackConfig:
    """Tests for YouTrackConfig dataclass."""

    def test_api_url(self, config: YouTrackConfig) -> None:
        """Test API URL construction."""
        assert config.api_url == "https://youtrack.example.com/api"

    def test_api_url_strips_trailing_slash(self) -> None:
        """Test that trailing slashes are stripped from URL."""
        config = YouTrackConfig(
            url="https://youtrack.example.com/",
            token="test-token",
        )
        assert config.api_url == "https://youtrack.example.com/api"

    def test_auth_header(self, config: YouTrackConfig) -> None:
        """Test authorization header format."""
        assert config.auth_header == {"Authorization": "Bearer test-token-123"}

    def test_default_values(self) -> None:
        """Test default configuration values."""
        config = YouTrackConfig(
            url="https://youtrack.example.com",
            token="test-token",
        )
        assert config.timeout == 30
        assert config.verify_ssl is True
        assert config.default_project is None


class TestLoadConfig:
    """Tests for load_config function."""

    def test_load_config_success(self) -> None:
        """Test successful config loading from environment."""
        env = {
            "YOUTRACK_URL": "https://youtrack.example.com",
            "YOUTRACK_TOKEN": "perm:test-token",
            "YOUTRACK_DEFAULT_PROJECT": "TEST",
            "YOUTRACK_TIMEOUT": "60",
            "YOUTRACK_VERIFY_SSL": "true",
        }
        with patch.dict(os.environ, env, clear=True):
            config = load_config()
            assert config.url == "https://youtrack.example.com"
            assert config.token == "perm:test-token"
            assert config.default_project == "TEST"
            assert config.timeout == 60
            assert config.verify_ssl is True

    def test_load_config_missing_url(self) -> None:
        """Test error when URL is missing."""
        env = {"YOUTRACK_TOKEN": "test-token"}
        with patch.dict(os.environ, env, clear=True), pytest.raises(SystemExit):
            load_config()

    def test_load_config_missing_token(self) -> None:
        """Test error when token is missing."""
        env = {"YOUTRACK_URL": "https://youtrack.example.com"}
        with patch.dict(os.environ, env, clear=True), pytest.raises(SystemExit):
            load_config()

    def test_load_config_invalid_timeout(self) -> None:
        """Test fallback when timeout is invalid."""
        env = {
            "YOUTRACK_URL": "https://youtrack.example.com",
            "YOUTRACK_TOKEN": "test-token",
            "YOUTRACK_TIMEOUT": "invalid",
        }
        with patch.dict(os.environ, env, clear=True):
            config = load_config()
            assert config.timeout == 30

    def test_load_config_ssl_verification_disabled(self) -> None:
        """Test SSL verification can be disabled."""
        env = {
            "YOUTRACK_URL": "https://youtrack.example.com",
            "YOUTRACK_TOKEN": "test-token",
            "YOUTRACK_VERIFY_SSL": "false",
        }
        with patch.dict(os.environ, env, clear=True):
            config = load_config()
            assert config.verify_ssl is False

    def test_load_config_ssl_verification_disabled_zero(self) -> None:
        """Test SSL verification can be disabled with 0."""
        env = {
            "YOUTRACK_URL": "https://youtrack.example.com",
            "YOUTRACK_TOKEN": "test-token",
            "YOUTRACK_VERIFY_SSL": "0",
        }
        with patch.dict(os.environ, env, clear=True):
            config = load_config()
            assert config.verify_ssl is False
