"""MCP tools for Jenkins operations."""

from .jobs import register_job_tools
from .builds import register_build_tools
from .logs import register_log_tools
from .scm import register_scm_tools
from .health import register_health_tools
from .advanced import register_advanced_tools
from .tests import register_test_tools


def register_all_tools(mcp_server, jenkins_adapter, config):
    """Register all tool handlers with the MCP server.

    Args:
        mcp_server: MCPServer instance
        jenkins_adapter: JenkinsAdapter instance
        config: JankinsConfig instance
    """
    register_job_tools(mcp_server, jenkins_adapter, config)
    register_build_tools(mcp_server, jenkins_adapter, config)
    register_log_tools(mcp_server, jenkins_adapter, config)
    register_scm_tools(mcp_server, jenkins_adapter, config)
    register_health_tools(mcp_server, jenkins_adapter, config)
    register_advanced_tools(mcp_server, jenkins_adapter, config)
    register_test_tools(mcp_server, jenkins_adapter, config)


__all__ = [
    "register_all_tools",
    "register_job_tools",
    "register_build_tools",
    "register_log_tools",
    "register_scm_tools",
    "register_health_tools",
    "register_advanced_tools",
    "register_test_tools",
]
