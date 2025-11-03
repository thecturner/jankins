"""Test configuration management."""

import pytest
from jankins.config import JankinsConfig


def test_config_from_values():
    """Test creating config from values."""
    config = JankinsConfig(
        jenkins_url="https://jenkins.example.com",
        jenkins_user="myuser",
        jenkins_api_token="mytoken",
    )

    assert config.jenkins_url == "https://jenkins.example.com"
    assert config.jenkins_user == "myuser"
    assert config.jenkins_api_token == "mytoken"
    assert config.mcp_transport == "http"  # Default
    assert config.mcp_bind == "127.0.0.1:8080"  # Default


def test_config_bind_parsing():
    """Test bind address parsing."""
    config = JankinsConfig(
        jenkins_url="http://localhost",
        jenkins_user="user",
        jenkins_api_token="token",
        mcp_bind="0.0.0.0:9000",
    )

    assert config.bind_host == "0.0.0.0"
    assert config.bind_port == 9000


def test_config_defaults():
    """Test default configuration values."""
    config = JankinsConfig(
        jenkins_url="http://localhost",
        jenkins_user="user",
        jenkins_api_token="token",
    )

    assert config.log_level == "INFO"
    assert config.log_json is False
    assert config.log_max_lines_default == 2000
    assert config.log_max_bytes_default == 262144
    assert config.jenkins_timeout == 30
    assert config.origin_enforce is False
