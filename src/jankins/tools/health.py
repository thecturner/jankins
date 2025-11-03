"""Health and auth-related MCP tools."""

import time
import uuid
import logging
from typing import Dict, Any

from ..mcp.protocol import Tool, ToolParameter, ToolParameterType
from ..formatters import OutputFormat, TokenAwareFormatter
from ..logging_utils import RequestLogger


logger = logging.getLogger(__name__)


def register_health_tools(mcp_server, jenkins_adapter, config):
    """Register health and auth tools."""

    # whoami
    async def whoami_handler(args: Dict[str, Any]) -> Dict[str, Any]:
        correlation_id = str(uuid.uuid4())
        start_time = time.time()

        with RequestLogger(logger, "whoami", correlation_id):
            whoami = jenkins_adapter.get_whoami()

            result = {
                "id": whoami.get("id"),
                "fullName": whoami.get("fullName"),
                "description": whoami.get("description"),
                "authorities": whoami.get("authorities", [])
            }

            took_ms = int((time.time() - start_time) * 1000)
            return TokenAwareFormatter.add_metadata(
                result, correlation_id, took_ms, OutputFormat.SUMMARY
            )

    mcp_server.register_tool(Tool(
        name="whoami",
        description="Get current authenticated user information",
        parameters=[],
        handler=whoami_handler
    ))

    # get_status
    async def get_status_handler(args: Dict[str, Any]) -> Dict[str, Any]:
        correlation_id = str(uuid.uuid4())
        start_time = time.time()

        with RequestLogger(logger, "get_status", correlation_id):
            # Get Jenkins version and queue info
            version = jenkins_adapter.get_version()
            queue = jenkins_adapter.get_queue_info()

            result = {
                "jenkins_version": version,
                "queue_length": len(queue),
                "status": "operational",
                "mcp_server": {
                    "name": mcp_server.name,
                    "version": mcp_server.version,
                }
            }

            took_ms = int((time.time() - start_time) * 1000)
            return TokenAwareFormatter.add_metadata(
                result, correlation_id, took_ms, OutputFormat.SUMMARY
            )

    mcp_server.register_tool(Tool(
        name="get_status",
        description="Get Jenkins server status and queue depth",
        parameters=[],
        handler=get_status_handler
    ))

    # summarize_queue
    async def summarize_queue_handler(args: Dict[str, Any]) -> Dict[str, Any]:
        correlation_id = str(uuid.uuid4())
        start_time = time.time()

        with RequestLogger(logger, "summarize_queue", correlation_id):
            queue = jenkins_adapter.get_queue_info()

            # Compact summary
            queue_items = []
            for item in queue[:20]:  # Top 20
                task = item.get("task", {})
                queue_items.append({
                    "id": item.get("id"),
                    "job": task.get("name"),
                    "why": item.get("why", "")[:100],  # Truncate reason
                    "blocked": item.get("blocked", False),
                    "stuck": item.get("stuck", False),
                })

            result = {
                "total_queued": len(queue),
                "shown": min(20, len(queue)),
                "blocked_count": sum(1 for i in queue if i.get("blocked")),
                "stuck_count": sum(1 for i in queue if i.get("stuck")),
                "items": queue_items
            }

            took_ms = int((time.time() - start_time) * 1000)
            return TokenAwareFormatter.add_metadata(
                result, correlation_id, took_ms, OutputFormat.SUMMARY
            )

    mcp_server.register_tool(Tool(
        name="summarize_queue",
        description="Get compact summary of Jenkins build queue",
        parameters=[],
        handler=summarize_queue_handler
    ))
