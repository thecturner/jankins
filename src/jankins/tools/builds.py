"""Build-related MCP tools."""

import time
import uuid
import logging
from typing import Dict, Any

from ..mcp.protocol import Tool, ToolParameter, ToolParameterType
from ..formatters import OutputFormat, TokenAwareFormatter
from ..logging_utils import RequestLogger
from ..errors import InvalidParamsError


logger = logging.getLogger(__name__)


def register_build_tools(mcp_server, jenkins_adapter, config):
    """Register build-related tools."""

    # get_build
    async def get_build_handler(args: Dict[str, Any]) -> Dict[str, Any]:
        correlation_id = str(uuid.uuid4())
        start_time = time.time()

        with RequestLogger(logger, "get_build", correlation_id):
            job_name = args["name"]
            number_or_last = args.get("number", "last")
            format_str = args.get("format", "summary")
            output_format = OutputFormat(format_str)

            # Get build number
            if number_or_last == "last":
                job_info = jenkins_adapter.get_job_info(job_name)
                last_build = job_info.get("lastBuild")
                if not last_build:
                    raise InvalidParamsError(
                        f"Job '{job_name}' has no builds",
                        hint="Trigger a build first"
                    )
                build_number = last_build["number"]
            else:
                try:
                    build_number = int(number_or_last)
                except ValueError:
                    raise InvalidParamsError(
                        f"Invalid build number: {number_or_last}",
                        hint="Provide a number or 'last'"
                    )

            build_info = jenkins_adapter.get_build_info(job_name, build_number)

            # Format response
            result = TokenAwareFormatter.format_build(build_info, format=output_format)

            took_ms = int((time.time() - start_time) * 1000)
            return TokenAwareFormatter.add_metadata(
                result, correlation_id, took_ms, output_format
            )

    mcp_server.register_tool(Tool(
        name="get_build",
        description="Get information about a specific build or the last build",
        parameters=[
            ToolParameter("name", ToolParameterType.STRING, "Full job name", required=True),
            ToolParameter("number", ToolParameterType.STRING, "Build number or 'last'", required=False, default="last"),
            ToolParameter("format", ToolParameterType.STRING, "Output format", required=False, default="summary", enum=["summary", "full", "ids"]),
        ],
        handler=get_build_handler
    ))

    # get_build_changes
    async def get_changes_handler(args: Dict[str, Any]) -> Dict[str, Any]:
        correlation_id = str(uuid.uuid4())
        start_time = time.time()

        with RequestLogger(logger, "get_build_changes", correlation_id):
            job_name = args["name"]
            number_or_last = args.get("number", "last")
            format_str = args.get("format", "summary")
            output_format = OutputFormat(format_str)

            # Get build number
            if number_or_last == "last":
                job_info = jenkins_adapter.get_job_info(job_name)
                last_build = job_info.get("lastBuild")
                if not last_build:
                    raise InvalidParamsError(f"Job '{job_name}' has no builds")
                build_number = last_build["number"]
            else:
                build_number = int(number_or_last)

            build_info = jenkins_adapter.get_build_info(job_name, build_number)
            change_set = build_info.get("changeSet", {})
            items = change_set.get("items", [])

            if output_format == OutputFormat.SUMMARY:
                result = {
                    "build_number": build_number,
                    "changes_count": len(items),
                    "changes": [
                        {
                            "commit": item.get("commitId", "")[:8],
                            "author": item.get("author", {}).get("fullName", "Unknown"),
                            "message": item.get("msg", "")[:100],  # Truncate message
                        }
                        for item in items[:10]  # Top 10 changes
                    ]
                }
            else:  # FULL
                result = {
                    "build_number": build_number,
                    "changes_count": len(items),
                    "changes": items
                }

            took_ms = int((time.time() - start_time) * 1000)
            return TokenAwareFormatter.add_metadata(
                result, correlation_id, took_ms, output_format
            )

    mcp_server.register_tool(Tool(
        name="get_build_changes",
        description="Get SCM changes (commits) for a build",
        parameters=[
            ToolParameter("name", ToolParameterType.STRING, "Full job name", required=True),
            ToolParameter("number", ToolParameterType.STRING, "Build number or 'last'", required=False, default="last"),
            ToolParameter("format", ToolParameterType.STRING, "Output format", required=False, default="summary", enum=["summary", "full"]),
        ],
        handler=get_changes_handler
    ))

    # get_build_artifacts
    async def get_artifacts_handler(args: Dict[str, Any]) -> Dict[str, Any]:
        correlation_id = str(uuid.uuid4())
        start_time = time.time()

        with RequestLogger(logger, "get_build_artifacts", correlation_id):
            job_name = args["name"]
            number_or_last = args.get("number", "last")
            format_str = args.get("format", "summary")
            output_format = OutputFormat(format_str)

            # Get build number
            if number_or_last == "last":
                job_info = jenkins_adapter.get_job_info(job_name)
                last_build = job_info.get("lastBuild")
                if not last_build:
                    raise InvalidParamsError(f"Job '{job_name}' has no builds")
                build_number = last_build["number"]
            else:
                build_number = int(number_or_last)

            build_info = jenkins_adapter.get_build_info(job_name, build_number)
            artifacts = build_info.get("artifacts", [])

            if output_format == OutputFormat.SUMMARY:
                result = {
                    "build_number": build_number,
                    "artifacts_count": len(artifacts),
                    "artifacts": [
                        {
                            "filename": a.get("fileName"),
                            "size": a.get("fileSize", 0),
                            "path": a.get("relativePath"),
                        }
                        for a in artifacts
                    ]
                }
            else:  # FULL
                result = {
                    "build_number": build_number,
                    "artifacts_count": len(artifacts),
                    "artifacts": artifacts,
                    "base_url": build_info.get("url")
                }

            took_ms = int((time.time() - start_time) * 1000)
            return TokenAwareFormatter.add_metadata(
                result, correlation_id, took_ms, output_format
            )

    mcp_server.register_tool(Tool(
        name="get_build_artifacts",
        description="Get artifacts produced by a build",
        parameters=[
            ToolParameter("name", ToolParameterType.STRING, "Full job name", required=True),
            ToolParameter("number", ToolParameterType.STRING, "Build number or 'last'", required=False, default="last"),
            ToolParameter("format", ToolParameterType.STRING, "Output format", required=False, default="summary", enum=["summary", "full"]),
        ],
        handler=get_artifacts_handler
    ))
