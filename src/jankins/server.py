"""Main server module that orchestrates MCP server components."""

import logging
from typing import Optional

from .config import JankinsConfig
from .jenkins import JenkinsAdapter
from .mcp import MCPServer, create_transport
from .tools import register_all_tools
from .prompts import register_prompts
from .logging_utils import setup_logging


logger = logging.getLogger(__name__)


class JankinsServer:
    """Main jankins MCP server.

    Coordinates configuration, Jenkins adapter, MCP protocol,
    and transport layers.
    """

    def __init__(self, config: JankinsConfig):
        """Initialize server with configuration.

        Args:
            config: Server configuration
        """
        self.config = config

        # Setup logging
        setup_logging(level=config.log_level, use_json=config.log_json)

        # Create Jenkins adapter
        self.jenkins_adapter = JenkinsAdapter(config)

        # Create MCP server
        self.mcp_server = MCPServer(name="jankins", version="0.2.1")

        # Register tools and prompts
        register_all_tools(self.mcp_server, self.jenkins_adapter, self.config)
        register_prompts(self.mcp_server, self.jenkins_adapter, self.config)

        logger.info(
            f"Initialized jankins MCP server",
            extra={
                "jenkins_url": config.jenkins_url,
                "transport": config.mcp_transport,
                "bind": config.mcp_bind,
                "tools_count": len(self.mcp_server.tools),
                "prompts_count": len(self.mcp_server.prompts),
            }
        )

    def create_app(self):
        """Create Starlette application.

        Returns:
            Starlette app
        """
        app = create_transport(
            self.mcp_server,
            self.config,
            transport_type=self.config.mcp_transport
        )

        logger.info(
            f"Created {self.config.mcp_transport} transport",
            extra={"bind": self.config.mcp_bind}
        )

        return app

    def close(self) -> None:
        """Clean up resources."""
        logger.info("Shutting down jankins server")
        self.jenkins_adapter.close()
