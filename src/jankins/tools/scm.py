"""SCM and pipeline-related MCP tools."""

import time
import uuid
import logging
from typing import Dict, Any

from ..mcp.protocol import Tool, ToolParameter, ToolParameterType
from ..formatters import OutputFormat, TokenAwareFormatter
from ..logging_utils import RequestLogger
from ..errors import InvalidParamsError


logger = logging.getLogger(__name__)


def register_scm_tools(mcp_server, jenkins_adapter, config):
    """Register SCM and pipeline tools."""

    # get_job_scm
    async def get_job_scm_handler(args: Dict[str, Any]) -> Dict[str, Any]:
        correlation_id = str(uuid.uuid4())
        start_time = time.time()

        with RequestLogger(logger, "get_job_scm", correlation_id):
            job_name = args["name"]
            format_str = args.get("format", "summary")
            output_format = OutputFormat(format_str)

            job_info = jenkins_adapter.get_job_info(job_name)
            scm = job_info.get("scm", {})

            if output_format == OutputFormat.SUMMARY:
                result = {
                    "job_name": job_name,
                    "scm_class": scm.get("_class", "unknown"),
                    "url": scm.get("userRemoteConfigs", [{}])[0].get("url") if scm.get("userRemoteConfigs") else None,
                    "branches": [
                        b.get("name") for b in scm.get("branches", [])
                    ]
                }
            else:  # FULL
                result = {
                    "job_name": job_name,
                    "scm": scm
                }

            took_ms = int((time.time() - start_time) * 1000)
            return TokenAwareFormatter.add_metadata(
                result, correlation_id, took_ms, output_format
            )

    mcp_server.register_tool(Tool(
        name="get_job_scm",
        description="Get SCM configuration for a job",
        parameters=[
            ToolParameter("name", ToolParameterType.STRING, "Full job name", required=True),
            ToolParameter("format", ToolParameterType.STRING, "Output format", required=False, default="summary", enum=["summary", "full"]),
        ],
        handler=get_job_scm_handler
    ))

    # get_build_scm
    async def get_build_scm_handler(args: Dict[str, Any]) -> Dict[str, Any]:
        correlation_id = str(uuid.uuid4())
        start_time = time.time()

        with RequestLogger(logger, "get_build_scm", correlation_id):
            job_name = args["name"]
            number_or_last = args.get("number", "last")

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

            # Extract SCM actions
            scm_actions = [
                action for action in build_info.get("actions", [])
                if action.get("_class", "").endswith("GitSCM") or
                   action.get("_class", "").endswith("SubversionSCM") or
                   "lastBuiltRevision" in action
            ]

            result = {
                "build_number": build_number,
                "job_name": job_name,
                "scm_info": scm_actions
            }

            took_ms = int((time.time() - start_time) * 1000)
            return TokenAwareFormatter.add_metadata(
                result, correlation_id, took_ms, OutputFormat.SUMMARY
            )

    mcp_server.register_tool(Tool(
        name="get_build_scm",
        description="Get SCM information (git commit, branch, etc.) for a build",
        parameters=[
            ToolParameter("name", ToolParameterType.STRING, "Full job name", required=True),
            ToolParameter("number", ToolParameterType.STRING, "Build number or 'last'", required=False, default="last"),
        ],
        handler=get_build_scm_handler
    ))
