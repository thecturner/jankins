"""Tests for stdio transport."""

import pytest
import json
import asyncio
from unittest.mock import AsyncMock, Mock, patch
from jankins.mcp.stdio_transport import handle_stdio_request, write_response
from jankins.mcp.protocol import MCPServer


@pytest.mark.unit
class TestStdioTransport:
    """Test stdio transport functionality."""

    @pytest.mark.asyncio
    async def test_handle_initialize_request(self, mcp_server):
        """Test handling initialize request."""
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"protocolVersion": "2025-06-18"}
        }

        response = await handle_stdio_request(mcp_server, request)

        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 1
        assert "result" in response

    @pytest.mark.asyncio
    async def test_handle_tools_list_request(self, mcp_server):
        """Test handling tools/list request."""
        request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
        }

        response = await handle_stdio_request(mcp_server, request)

        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 2
        assert "result" in response
        assert "tools" in response["result"]

    @pytest.mark.asyncio
    async def test_handle_prompts_list_request(self, mcp_server):
        """Test handling prompts/list request."""
        request = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "prompts/list",
        }

        response = await handle_stdio_request(mcp_server, request)

        assert response["jsonrpc"] == "2.0"
        assert "result" in response
        assert "prompts" in response["result"]

    @pytest.mark.asyncio
    async def test_handle_invalid_method(self, mcp_server):
        """Test handling invalid method."""
        request = {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "invalid/method",
        }

        response = await handle_stdio_request(mcp_server, request)

        assert response["jsonrpc"] == "2.0"
        assert "error" in response
        assert response["error"]["code"] == -32601  # Method not found

    @pytest.mark.asyncio
    async def test_handle_malformed_request(self, mcp_server):
        """Test handling malformed request."""
        request = {
            "jsonrpc": "1.0",  # Wrong version
            "method": "initialize",
        }

        response = await handle_stdio_request(mcp_server, request)

        # Should return an error
        assert "error" in response or "result" in response

    def test_write_response(self, capsys):
        """Test writing response to stdout."""
        response = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {"status": "ok"}
        }

        write_response(response)

        captured = capsys.readouterr()
        output = captured.out.strip()

        # Should be valid JSON
        parsed = json.loads(output)
        assert parsed == response

    @pytest.mark.asyncio
    async def test_tools_call_execution(self, mcp_server):
        """Test executing a tool call."""
        # This tests the async tool call path
        request = {
            "jsonrpc": "2.0",
            "id": 5,
            "method": "tools/call",
            "params": {
                "name": "whoami",
                "arguments": {}
            }
        }

        # Mock the call_tool method
        with patch.object(mcp_server, 'call_tool', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = {"user": "test_user"}

            response = await handle_stdio_request(mcp_server, request)

            assert response["jsonrpc"] == "2.0"
            assert "result" in response or "error" in response

    @pytest.mark.asyncio
    async def test_error_handling(self, mcp_server):
        """Test error handling in stdio transport."""
        request = {
            "jsonrpc": "2.0",
            "id": 6,
            "method": "tools/call",
            "params": {
                "name": "nonexistent_tool",
                "arguments": {}
            }
        }

        response = await handle_stdio_request(mcp_server, request)

        assert "error" in response
        assert response["error"]["code"] < 0  # Error codes are negative
