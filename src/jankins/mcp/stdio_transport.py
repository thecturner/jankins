"""MCP stdio transport for communication via stdin/stdout.

This transport is used by MCP clients like Claude Desktop that communicate
with servers over standard input/output streams.
"""

import sys
import json
import logging
import asyncio
from typing import Optional

from .protocol import MCPServer
from ..errors import JankinsError


logger = logging.getLogger(__name__)


async def run_stdio_server(mcp_server: MCPServer) -> None:
    """Run MCP server in stdio mode.

    Reads JSON-RPC messages from stdin (line by line) and writes responses to stdout.
    All logging goes to stderr to avoid interfering with the protocol.

    Args:
        mcp_server: MCP server instance
    """
    logger.info("Starting jankins MCP server in stdio mode", extra={
        "tools": len(mcp_server.tools),
        "prompts": len(mcp_server.prompts)
    })

    # Ensure stdout is line-buffered for immediate response delivery
    sys.stdout.reconfigure(line_buffering=True)

    try:
        # Read from stdin line by line
        while True:
            try:
                # Read a line from stdin
                line = await asyncio.get_event_loop().run_in_executor(
                    None, sys.stdin.readline
                )

                if not line:
                    # EOF - client closed connection
                    logger.info("Stdin closed, shutting down")
                    break

                line = line.strip()
                if not line:
                    continue

                logger.debug(f"Received request: {line[:100]}...")

                # Parse JSON-RPC request
                try:
                    request = json.loads(line)
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON: {e}")
                    response = {
                        "jsonrpc": "2.0",
                        "error": {
                            "code": -32700,
                            "message": "Parse error: Invalid JSON"
                        },
                        "id": None
                    }
                    write_response(response)
                    continue

                # Handle the request
                response = await handle_stdio_request(mcp_server, request)

                # Write response to stdout
                write_response(response)

            except KeyboardInterrupt:
                logger.info("Received interrupt signal, shutting down")
                break
            except Exception as e:
                logger.exception("Error processing stdin request")
                # Send error response if we have a request ID
                error_response = {
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32603,
                        "message": "Internal error",
                        "data": {"hint": str(e)}
                    },
                    "id": None
                }
                write_response(error_response)

    except Exception as e:
        logger.exception("Fatal error in stdio server")
        sys.exit(1)

    logger.info("jankins stdio server stopped")


async def handle_stdio_request(
    mcp_server: MCPServer,
    request: dict
) -> dict:
    """Handle a single JSON-RPC request.

    Args:
        mcp_server: MCP server instance
        request: JSON-RPC request dictionary

    Returns:
        JSON-RPC response dictionary
    """
    # Handle the request through MCP protocol
    try:
        response = mcp_server.handle_jsonrpc(request)

        # If response indicates async method, execute it
        if response.get("_async"):
            method = response["method"]
            params = response["params"]
            request_id = response["id"]

            try:
                if method == "tools/call":
                    result = await mcp_server.call_tool(
                        params.get("name"),
                        params.get("arguments", {})
                    )
                    response = {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": result
                    }
                elif method == "prompts/get":
                    messages = await mcp_server.get_prompt(
                        params.get("name"),
                        params.get("arguments", {})
                    )
                    response = {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": {"messages": messages}
                    }
                else:
                    # Unknown async method
                    response = {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {
                            "code": -32601,
                            "message": f"Method not found: {method}"
                        }
                    }
            except JankinsError as e:
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": e.to_dict()
                }
            except Exception as e:
                logger.exception(f"Error executing async method {method}")
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32603,
                        "message": "Internal error",
                        "data": {"hint": str(e)}
                    }
                }

        return response

    except Exception as e:
        logger.exception("Error handling JSON-RPC request")
        return {
            "jsonrpc": "2.0",
            "error": {
                "code": -32603,
                "message": "Internal error",
                "data": {"hint": str(e)}
            },
            "id": request.get("id")
        }


def write_response(response: dict) -> None:
    """Write JSON-RPC response to stdout.

    Args:
        response: JSON-RPC response dictionary
    """
    try:
        response_json = json.dumps(response)
        logger.debug(f"Sending response: {response_json[:100]}...")
        print(response_json, flush=True)
    except Exception as e:
        logger.exception("Error writing response to stdout")
