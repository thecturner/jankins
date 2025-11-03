"""Test MCP protocol implementation."""

import pytest
from jankins.mcp.protocol import (
    MCPServer,
    Tool,
    ToolParameter,
    ToolParameterType,
    MCP_VERSION,
)
from jankins.errors import InvalidParamsError


def test_mcp_server_creation():
    """Test MCP server initialization."""
    server = MCPServer(name="test", version="1.0.0")

    assert server.name == "test"
    assert server.version == "1.0.0"
    assert len(server.tools) == 0


def test_tool_registration():
    """Test tool registration."""
    server = MCPServer()

    async def test_handler(args):
        return {"result": "success"}

    tool = Tool(
        name="test_tool",
        description="A test tool",
        parameters=[
            ToolParameter("arg1", ToolParameterType.STRING, "First arg", required=True)
        ],
        handler=test_handler
    )

    server.register_tool(tool)

    assert "test_tool" in server.tools
    assert server.tools["test_tool"].name == "test_tool"


def test_get_capabilities():
    """Test capabilities response."""
    server = MCPServer(name="test", version="1.0.0")
    caps = server.get_capabilities()

    assert "capabilities" in caps
    assert "serverInfo" in caps
    assert caps["serverInfo"]["name"] == "test"
    assert caps["serverInfo"]["version"] == "1.0.0"
    assert caps["protocolVersion"] == MCP_VERSION


def test_list_tools():
    """Test tools listing."""
    server = MCPServer()

    async def handler(args):
        return {}

    tool1 = Tool("tool1", "First tool", handler=handler)
    tool2 = Tool("tool2", "Second tool", handler=handler)

    server.register_tool(tool1)
    server.register_tool(tool2)

    tools_list = server.list_tools()

    assert len(tools_list) == 2
    assert tools_list[0]["name"] == "tool1"
    assert tools_list[1]["name"] == "tool2"


def test_tool_schema_generation():
    """Test tool schema generation."""
    async def handler(args):
        return {}

    tool = Tool(
        name="my_tool",
        description="My test tool",
        parameters=[
            ToolParameter("name", ToolParameterType.STRING, "Name parameter", required=True),
            ToolParameter("count", ToolParameterType.NUMBER, "Count parameter", required=False, default=10),
        ],
        handler=handler
    )

    schema = tool.to_schema()

    assert schema["name"] == "my_tool"
    assert schema["description"] == "My test tool"
    assert "inputSchema" in schema
    assert "name" in schema["inputSchema"]["properties"]
    assert "count" in schema["inputSchema"]["properties"]
    assert "name" in schema["inputSchema"]["required"]
    assert "count" not in schema["inputSchema"]["required"]


@pytest.mark.asyncio
async def test_call_tool_success():
    """Test successful tool call."""
    server = MCPServer()

    async def add_handler(args):
        return {"sum": args["a"] + args["b"]}

    tool = Tool(
        name="add",
        description="Add two numbers",
        parameters=[
            ToolParameter("a", ToolParameterType.NUMBER, "First number", required=True),
            ToolParameter("b", ToolParameterType.NUMBER, "Second number", required=True),
        ],
        handler=add_handler
    )

    server.register_tool(tool)

    result = await server.call_tool("add", {"a": 5, "b": 3})

    assert result["sum"] == 8


@pytest.mark.asyncio
async def test_call_tool_not_found():
    """Test calling non-existent tool."""
    server = MCPServer()

    with pytest.raises(InvalidParamsError) as exc_info:
        await server.call_tool("nonexistent", {})

    assert "not found" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_call_tool_missing_params():
    """Test calling tool with missing required parameters."""
    server = MCPServer()

    async def handler(args):
        return {}

    tool = Tool(
        name="test",
        description="Test",
        parameters=[
            ToolParameter("required_param", ToolParameterType.STRING, "Required", required=True)
        ],
        handler=handler
    )

    server.register_tool(tool)

    with pytest.raises(InvalidParamsError) as exc_info:
        await server.call_tool("test", {})

    assert "missing" in str(exc_info.value).lower()
