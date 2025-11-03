"""Job-related MCP tools."""

import time
import uuid
import logging
from typing import Dict, Any

from ..mcp.protocol import Tool, ToolParameter, ToolParameterType
from ..formatters import OutputFormat, TokenAwareFormatter
from ..logging_utils import RequestLogger


logger = logging.getLogger(__name__)


def register_job_tools(mcp_server, jenkins_adapter, config):
    """Register job-related tools."""

    # list_jobs
    async def list_jobs_handler(args: Dict[str, Any]) -> Dict[str, Any]:
        correlation_id = str(uuid.uuid4())
        start_time = time.time()

        with RequestLogger(logger, "list_jobs", correlation_id):
            prefix = args.get("prefix", "")
            page = args.get("page", 1)
            page_size = args.get("page_size", 50)
            format_str = args.get("format", "summary")
            output_format = OutputFormat(format_str)

            # Get all jobs
            all_jobs = jenkins_adapter.get_all_jobs(folder_depth=10)

            # Filter by prefix if provided
            if prefix:
                all_jobs = [j for j in all_jobs if j["fullname"].startswith(prefix)]

            # Pagination
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            page_jobs = all_jobs[start_idx:end_idx]

            # Format response
            result = TokenAwareFormatter.format_job_list(
                page_jobs,
                format=output_format,
                limit=page_size
            )

            result["page"] = page
            result["page_size"] = page_size
            result["total_pages"] = (len(all_jobs) + page_size - 1) // page_size

            took_ms = int((time.time() - start_time) * 1000)
            return TokenAwareFormatter.add_metadata(
                result, correlation_id, took_ms, output_format
            )

    mcp_server.register_tool(Tool(
        name="list_jobs",
        description="List Jenkins jobs with optional prefix filtering and pagination",
        parameters=[
            ToolParameter("prefix", ToolParameterType.STRING, "Job name prefix filter", required=False),
            ToolParameter("page", ToolParameterType.NUMBER, "Page number (1-indexed)", required=False, default=1),
            ToolParameter("page_size", ToolParameterType.NUMBER, "Items per page", required=False, default=50),
            ToolParameter("format", ToolParameterType.STRING, "Output format", required=False, default="summary", enum=["summary", "full", "ids"]),
        ],
        handler=list_jobs_handler
    ))

    # get_job
    async def get_job_handler(args: Dict[str, Any]) -> Dict[str, Any]:
        correlation_id = str(uuid.uuid4())
        start_time = time.time()

        with RequestLogger(logger, "get_job", correlation_id):
            job_name = args["name"]
            format_str = args.get("format", "summary")
            output_format = OutputFormat(format_str)

            job_info = jenkins_adapter.get_job_info(job_name)

            # Format based on output format
            if output_format == OutputFormat.IDS:
                result = {
                    "name": job_info["name"],
                    "fullname": job_info["fullName"],
                    "url": job_info["url"],
                }
            elif output_format == OutputFormat.SUMMARY:
                result = {
                    "name": job_info["name"],
                    "fullname": job_info["fullName"],
                    "url": job_info["url"],
                    "buildable": job_info.get("buildable", False),
                    "color": job_info.get("color", "unknown"),
                    "last_build": job_info.get("lastBuild", {}).get("number") if job_info.get("lastBuild") else None,
                    "last_successful_build": job_info.get("lastSuccessfulBuild", {}).get("number") if job_info.get("lastSuccessfulBuild") else None,
                    "last_failed_build": job_info.get("lastFailedBuild", {}).get("number") if job_info.get("lastFailedBuild") else None,
                    "health_report": [
                        {"description": h.get("description"), "score": h.get("score")}
                        for h in job_info.get("healthReport", [])
                    ][:3]  # Top 3 health reports
                }
            else:  # FULL
                result = job_info

            took_ms = int((time.time() - start_time) * 1000)
            return TokenAwareFormatter.add_metadata(
                result, correlation_id, took_ms, output_format
            )

    mcp_server.register_tool(Tool(
        name="get_job",
        description="Get detailed information about a specific Jenkins job",
        parameters=[
            ToolParameter("name", ToolParameterType.STRING, "Full job name (e.g., 'folder/subfolder/job')", required=True),
            ToolParameter("format", ToolParameterType.STRING, "Output format", required=False, default="summary", enum=["summary", "full", "ids"]),
        ],
        handler=get_job_handler
    ))

    # trigger_build
    async def trigger_build_handler(args: Dict[str, Any]) -> Dict[str, Any]:
        correlation_id = str(uuid.uuid4())
        start_time = time.time()

        with RequestLogger(logger, "trigger_build", correlation_id):
            job_name = args["name"]
            parameters = args.get("parameters", {})

            queue_id = jenkins_adapter.build_job(job_name, parameters=parameters)

            result = {
                "queue_id": queue_id,
                "job_name": job_name,
                "parameters": parameters,
                "status": "queued",
                "message": f"Build queued for {job_name}",
            }

            took_ms = int((time.time() - start_time) * 1000)
            return TokenAwareFormatter.add_metadata(
                result, correlation_id, took_ms, OutputFormat.SUMMARY
            )

    mcp_server.register_tool(Tool(
        name="trigger_build",
        description="Trigger a new build for a Jenkins job with optional parameters",
        parameters=[
            ToolParameter("name", ToolParameterType.STRING, "Full job name", required=True),
            ToolParameter("parameters", ToolParameterType.OBJECT, "Build parameters as key-value pairs", required=False, default={}),
        ],
        handler=trigger_build_handler
    ))

    # enable_job
    async def enable_job_handler(args: Dict[str, Any]) -> Dict[str, Any]:
        correlation_id = str(uuid.uuid4())
        start_time = time.time()

        with RequestLogger(logger, "enable_job", correlation_id):
            job_name = args["name"]
            jenkins_adapter.enable_job(job_name)

            result = {
                "job_name": job_name,
                "status": "enabled",
                "message": f"Job {job_name} has been enabled",
            }

            took_ms = int((time.time() - start_time) * 1000)
            return TokenAwareFormatter.add_metadata(
                result, correlation_id, took_ms, OutputFormat.SUMMARY
            )

    mcp_server.register_tool(Tool(
        name="enable_job",
        description="Enable a Jenkins job to allow builds",
        parameters=[
            ToolParameter("name", ToolParameterType.STRING, "Full job name", required=True),
        ],
        handler=enable_job_handler
    ))

    # disable_job
    async def disable_job_handler(args: Dict[str, Any]) -> Dict[str, Any]:
        correlation_id = str(uuid.uuid4())
        start_time = time.time()

        with RequestLogger(logger, "disable_job", correlation_id):
            job_name = args["name"]
            jenkins_adapter.disable_job(job_name)

            result = {
                "job_name": job_name,
                "status": "disabled",
                "message": f"Job {job_name} has been disabled",
            }

            took_ms = int((time.time() - start_time) * 1000)
            return TokenAwareFormatter.add_metadata(
                result, correlation_id, took_ms, OutputFormat.SUMMARY
            )

    mcp_server.register_tool(Tool(
        name="disable_job",
        description="Disable a Jenkins job to prevent builds",
        parameters=[
            ToolParameter("name", ToolParameterType.STRING, "Full job name", required=True),
        ],
        handler=disable_job_handler
    ))
