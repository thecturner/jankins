"""MCP transport implementations: HTTP and SSE.

Provides both HTTP streamable and Server-Sent Events transports
for MCP protocol communication.
"""

import json
import logging
from typing import Optional
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response, StreamingResponse
from starlette.routing import Route
from sse_starlette.sse import EventSourceResponse

from .protocol import MCPServer
from ..config import JankinsConfig
from ..errors import JankinsError


logger = logging.getLogger(__name__)


async def handle_mcp_request(request: Request) -> Response:
    """Handle MCP HTTP request.

    Supports both single requests and streaming.
    """
    mcp_server: MCPServer = request.app.state.mcp_server
    config: JankinsConfig = request.app.state.config

    # Origin validation if enforced
    if config.origin_enforce:
        origin = request.headers.get("origin", "")
        if config.origin_expected and origin != config.origin_expected:
            return JSONResponse(
                {
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32000,
                        "message": "Origin not allowed",
                        "data": {
                            "expected": config.origin_expected,
                            "received": origin
                        }
                    }
                },
                status_code=403
            )

    try:
        body = await request.json()
    except json.JSONDecodeError:
        return JSONResponse(
            {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32700,
                    "message": "Parse error: Invalid JSON"
                }
            },
            status_code=400
        )

    # Handle the request
    try:
        response = mcp_server.handle_jsonrpc(body)

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
            except JankinsError as e:
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": e.to_dict()
                }

        return JSONResponse(response)

    except Exception as e:
        logger.exception("Unexpected error handling MCP request")
        return JSONResponse(
            {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32603,
                    "message": "Internal error",
                    "data": {
                        "hint": "Check server logs for details"
                    }
                }
            },
            status_code=500
        )


async def handle_sse(request: Request) -> EventSourceResponse:
    """Handle MCP SSE request.

    Provides Server-Sent Events endpoint for long-lived connections.
    """
    mcp_server: MCPServer = request.app.state.mcp_server
    config: JankinsConfig = request.app.state.config

    # Origin validation if enforced
    if config.origin_enforce:
        origin = request.headers.get("origin", "")
        if config.origin_expected and origin != config.origin_expected:
            return JSONResponse(
                {"error": "Origin not allowed"},
                status_code=403
            )

    async def event_generator():
        """Generate SSE events."""
        # Send initial connection event
        yield {
            "event": "connected",
            "data": json.dumps({
                "server": mcp_server.name,
                "version": mcp_server.version
            })
        }

        # In a real implementation, this would handle bidirectional
        # communication. For now, we keep the connection alive.
        # Clients can POST to /mcp for requests.

    return EventSourceResponse(event_generator())


async def handle_health(request: Request) -> JSONResponse:
    """Health check endpoint."""
    return JSONResponse({"status": "ok"})


async def handle_ready(request: Request) -> JSONResponse:
    """Readiness check endpoint."""
    # Could check Jenkins connectivity here
    return JSONResponse({"status": "ready"})


async def handle_metrics(request: Request) -> Response:
    """Metrics endpoint (placeholder for Prometheus)."""
    return Response(
        content="# Metrics not yet implemented\n",
        media_type="text/plain"
    )


def create_transport(
    mcp_server: MCPServer,
    config: JankinsConfig,
    transport_type: str = "http"
) -> Starlette:
    """Create Starlette application with MCP transport.

    Args:
        mcp_server: MCP server instance
        config: Configuration
        transport_type: "http" or "sse"

    Returns:
        Starlette application
    """
    routes = [
        Route("/mcp", handle_mcp_request, methods=["POST"]),
        Route("/_health", handle_health, methods=["GET"]),
        Route("/_ready", handle_ready, methods=["GET"]),
        Route("/_metrics", handle_metrics, methods=["GET"]),
    ]

    # Add SSE endpoint if requested
    if transport_type == "sse":
        routes.append(Route("/sse", handle_sse, methods=["GET"]))

    app = Starlette(debug=False, routes=routes)

    # Store dependencies in app state
    app.state.mcp_server = mcp_server
    app.state.config = config

    return app
