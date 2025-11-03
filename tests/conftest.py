"""Pytest fixtures for jankins tests."""

import pytest
from unittest.mock import Mock

from jankins.config import JankinsConfig
from jankins.jenkins import JenkinsAdapter
from jankins.mcp import MCPServer


@pytest.fixture
def test_config():
    """Create test configuration."""
    return JankinsConfig(
        jenkins_url="http://localhost:8080",
        jenkins_user="test_user",
        jenkins_api_token="test_token",
        mcp_transport="http",
        mcp_bind="127.0.0.1:8080",
        log_level="DEBUG",
    )


@pytest.fixture
def mock_jenkins_adapter(test_config):
    """Create mock Jenkins adapter."""
    adapter = Mock(spec=JenkinsAdapter)
    adapter.config = test_config
    return adapter


@pytest.fixture
def mcp_server():
    """Create MCP server instance."""
    return MCPServer(name="jankins-test", version="0.1.0")
