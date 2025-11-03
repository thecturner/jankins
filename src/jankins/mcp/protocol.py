"""MCP protocol handler implementing the Model Context Protocol spec.

Implements MCP version 2025-06-18 with proper capabilities and tool handling.
"""

import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, cast

from ..errors import InvalidParamsError, JankinsError

logger = logging.getLogger(__name__)


MCP_VERSION = "2025-06-18"


class ToolParameterType(str, Enum):
    """MCP tool parameter types."""

    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"
    OBJECT = "object"
    ARRAY = "array"


@dataclass
class ToolParameter:
    """MCP tool parameter definition."""

    name: str
    type: ToolParameterType
    description: str
    required: bool = False
    default: Any | None = None
    enum: list[str] | None = None


@dataclass
class Tool:
    """MCP tool definition."""

    name: str
    description: str
    parameters: list[ToolParameter] = field(default_factory=list)
    handler: Callable[[dict[str, Any]], Awaitable[dict[str, Any]]] | None = None

    def to_schema(self) -> dict[str, Any]:
        """Convert tool to MCP schema format."""
        input_schema: dict[str, Any] = {"type": "object", "properties": {}, "required": []}
        schema = {
            "name": self.name,
            "description": self.description,
            "inputSchema": input_schema,
        }

        properties = cast(dict[str, Any], input_schema["properties"])
        required = cast(list[str], input_schema["required"])

        for param in self.parameters:
            param_schema: dict[str, Any] = {
                "type": param.type.value,
                "description": param.description,
            }

            if param.enum:
                param_schema["enum"] = param.enum

            if param.default is not None:
                param_schema["default"] = param.default

            properties[param.name] = param_schema

            if param.required:
                required.append(param.name)

        return schema


@dataclass
class Prompt:
    """MCP prompt definition."""

    name: str
    description: str
    arguments: list[ToolParameter] = field(default_factory=list)
    handler: Callable[[dict[str, Any]], Awaitable[list[dict[str, Any]]]] | None = None

    def to_schema(self) -> dict[str, Any]:
        """Convert prompt to MCP schema format."""
        schema: dict[str, Any] = {
            "name": self.name,
            "description": self.description,
        }

        if self.arguments:
            schema["arguments"] = [
                {
                    "name": arg.name,
                    "description": arg.description,
                    "required": arg.required,
                }
                for arg in self.arguments
            ]

        return schema


class MCPServer:
    """MCP protocol server implementation.

    Handles tool registration, capability negotiation, and request routing.
    """

    def __init__(self, name: str = "jankins", version: str = "0.1.0"):
        self.name = name
        self.version = version
        self.tools: dict[str, Tool] = {}
        self.prompts: dict[str, Prompt] = {}

    def register_tool(self, tool: Tool) -> None:
        """Register a tool with the server."""
        self.tools[tool.name] = tool
        logger.debug(f"Registered tool: {tool.name}")

    def register_prompt(self, prompt: Prompt) -> None:
        """Register a prompt with the server."""
        self.prompts[prompt.name] = prompt
        logger.debug(f"Registered prompt: {prompt.name}")

    def get_capabilities(self) -> dict[str, Any]:
        """Get server capabilities."""
        return {
            "capabilities": {
                "tools": {
                    "listChanged": False  # We don't dynamically change tools
                },
                "prompts": {"listChanged": False},
            },
            "serverInfo": {
                "name": self.name,
                "version": self.version,
            },
            "protocolVersion": MCP_VERSION,
        }

    def list_tools(self) -> list[dict[str, Any]]:
        """List all registered tools."""
        return [tool.to_schema() for tool in self.tools.values()]

    def list_prompts(self) -> list[dict[str, Any]]:
        """List all registered prompts."""
        return [prompt.to_schema() for prompt in self.prompts.values()]

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Call a tool by name with arguments.

        Args:
            name: Tool name
            arguments: Tool arguments

        Returns:
            Tool result

        Raises:
            InvalidParamsError: If tool not found or arguments invalid
            JankinsError: If tool execution fails
        """
        if name not in self.tools:
            raise InvalidParamsError(
                f"Tool '{name}' not found", hint=f"Available tools: {', '.join(self.tools.keys())}"
            )

        tool = self.tools[name]

        if not tool.handler:
            raise InvalidParamsError(
                f"Tool '{name}' has no handler registered",
                hint="This is a server configuration error",
            )

        # Validate required parameters
        required_params = [p.name for p in tool.parameters if p.required]
        missing_params = [p for p in required_params if p not in arguments]

        if missing_params:
            raise InvalidParamsError(
                f"Missing required parameters: {', '.join(missing_params)}",
                hint=f"Tool '{name}' requires: {', '.join(required_params)}",
            )

        try:
            return await tool.handler(arguments)
        except JankinsError:
            raise  # Re-raise JankinsErrors as-is
        except Exception as e:
            logger.exception(f"Tool '{name}' handler failed")
            raise JankinsError(
                f"Tool execution failed: {str(e)}", hint="Check server logs for details"
            )

    async def get_prompt(self, name: str, arguments: dict[str, Any]) -> list[dict[str, Any]]:
        """Get prompt messages by name.

        Args:
            name: Prompt name
            arguments: Prompt arguments

        Returns:
            List of prompt messages

        Raises:
            InvalidParamsError: If prompt not found
        """
        if name not in self.prompts:
            raise InvalidParamsError(
                f"Prompt '{name}' not found",
                hint=f"Available prompts: {', '.join(self.prompts.keys())}",
            )

        prompt = self.prompts[name]

        if not prompt.handler:
            raise InvalidParamsError(
                f"Prompt '{name}' has no handler registered",
                hint="This is a server configuration error",
            )

        try:
            return await prompt.handler(arguments)
        except Exception as e:
            logger.exception(f"Prompt '{name}' handler failed")
            raise JankinsError(
                f"Prompt execution failed: {str(e)}", hint="Check server logs for details"
            )

    def handle_jsonrpc(self, request: dict[str, Any]) -> dict[str, Any]:
        """Handle a JSON-RPC 2.0 request.

        This is a synchronous wrapper that routes to async handlers.
        The actual async execution happens in the transport layer.

        Args:
            request: JSON-RPC request

        Returns:
            JSON-RPC response or error
        """
        method = request.get("method")
        params = request.get("params", {})
        request_id = request.get("id")

        # Initialize response
        if method == "initialize":
            return {"jsonrpc": "2.0", "id": request_id, "result": self.get_capabilities()}

        elif method == "tools/list":
            return {"jsonrpc": "2.0", "id": request_id, "result": {"tools": self.list_tools()}}

        elif method == "prompts/list":
            return {"jsonrpc": "2.0", "id": request_id, "result": {"prompts": self.list_prompts()}}

        # For async methods (tools/call, prompts/get), return a marker
        # The transport layer will handle the async execution
        elif method in ["tools/call", "prompts/get"]:
            return {"_async": True, "method": method, "params": params, "id": request_id}

        else:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}",
                    "data": {"hint": "Check MCP protocol documentation for valid methods"},
                },
            }
