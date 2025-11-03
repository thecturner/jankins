"""Pytest fixtures for jankins tests."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest

from jankins.cache import ResponseCache
from jankins.config import JankinsConfig
from jankins.jenkins import JenkinsAdapter
from jankins.mcp import MCPServer
from jankins.metrics import MetricsCollector


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
def test_config_stdio():
    """Create test configuration for stdio transport."""
    return JankinsConfig(
        jenkins_url="http://localhost:8080",
        jenkins_user="test_user",
        jenkins_api_token="test_token",
        mcp_transport="stdio",
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
    return MCPServer(name="jankins-test", version="0.2.1")


@pytest.fixture
def mock_jenkins_client():
    """Create mock Jenkins client with common responses."""
    client = MagicMock()

    # Mock job info
    client.get_job_info.return_value = {
        "name": "test-job",
        "url": "http://localhost:8080/job/test-job/",
        "buildable": True,
        "lastBuild": {"number": 42},
        "lastSuccessfulBuild": {"number": 41},
        "lastFailedBuild": {"number": 40},
    }

    # Mock build info
    client.get_build_info.return_value = {
        "number": 42,
        "result": "SUCCESS",
        "duration": 120000,
        "timestamp": 1704067200000,
        "url": "http://localhost:8080/job/test-job/42/",
    }

    # Mock log
    client.get_build_console_output.return_value = "Build log output\nSUCCESS"

    # Mock whoami
    client.get_whoami.return_value = {
        "name": "test_user",
        "fullName": "Test User",
    }

    return client


@pytest.fixture
def sample_build_data() -> dict[str, Any]:
    """Sample build data for testing."""
    return {
        "number": 42,
        "result": "FAILURE",
        "duration": 125000,
        "timestamp": 1704067200000,
        "url": "http://localhost:8080/job/test-job/42/",
        "changeSet": {
            "items": [
                {
                    "commitId": "abc123",
                    "author": {"fullName": "Test User"},
                    "msg": "Fix bug",
                }
            ]
        },
    }


@pytest.fixture
def sample_test_report() -> dict[str, Any]:
    """Sample test report data for testing."""
    return {
        "duration": 15.5,
        "failCount": 2,
        "passCount": 98,
        "skipCount": 0,
        "suites": [
            {
                "name": "TestSuite1",
                "cases": [
                    {
                        "className": "test.TestClass",
                        "name": "test_success",
                        "status": "PASSED",
                        "duration": 0.1,
                    },
                    {
                        "className": "test.TestClass",
                        "name": "test_failure",
                        "status": "FAILED",
                        "duration": 0.2,
                        "errorDetails": "AssertionError: Expected 1, got 2",
                        "errorStackTrace": "Traceback...",
                    },
                ],
            }
        ],
    }


@pytest.fixture
def sample_blueocean_nodes() -> list:
    """Sample Blue Ocean pipeline nodes for testing."""
    return [
        {
            "id": "1",
            "displayName": "Build",
            "durationInMillis": 5000,
            "result": "SUCCESS",
            "type": "STAGE",
        },
        {
            "id": "2",
            "displayName": "Test",
            "durationInMillis": 10000,
            "result": "FAILURE",
            "type": "STAGE",
        },
    ]


@pytest.fixture
def response_cache():
    """Create response cache instance."""
    return ResponseCache(ttl_seconds=60, max_size=100)


@pytest.fixture
def metrics_collector():
    """Create metrics collector instance."""
    return MetricsCollector()


@pytest.fixture
def mock_httpx_client():
    """Create mock httpx client."""
    client = AsyncMock()
    response = AsyncMock()
    response.status_code = 200
    response.json.return_value = {"status": "ok"}
    response.text = "OK"
    client.get.return_value = response
    client.post.return_value = response
    return client


@pytest.fixture
def sample_maven_log() -> str:
    """Sample Maven build log for testing."""
    return """
[INFO] Scanning for projects...
[INFO] Building test-project 1.0.0-SNAPSHOT
[INFO] --------------------------------[ jar ]---------------------------------
[ERROR] Failed to execute goal org.apache.maven.plugins:maven-compiler-plugin:3.8.1:compile
[ERROR] Compilation failure
[ERROR] /path/to/file.java:[10,5] cannot find symbol
[ERROR]   symbol:   class NonExistentClass
[ERROR]   location: class TestClass
[INFO] BUILD FAILURE
"""


@pytest.fixture
def sample_gradle_log() -> str:
    """Sample Gradle build log for testing."""
    return """
> Task :compileJava FAILED
/path/to/file.java:10: error: cannot find symbol
  symbol:   class NonExistentClass
  location: class TestClass
1 error

FAILURE: Build failed with an exception.
* What went wrong:
Execution failed for task ':compileJava'.
> Compilation failed; see the compiler error output for details.
"""


@pytest.fixture
def sample_npm_log() -> str:
    """Sample NPM build log for testing."""
    return """
npm ERR! code ENOENT
npm ERR! syscall open
npm ERR! path /path/to/package.json
npm ERR! errno -2
npm ERR! enoent ENOENT: no such file or directory, open '/path/to/package.json'

npm ERR! A complete log of this run can be found in:
npm ERR!     /path/to/npm-cache/_logs/2024-01-01T00_00_00_000Z-debug.log
"""
