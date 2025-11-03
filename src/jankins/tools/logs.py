"""Log-related MCP tools with smart truncation and filtering."""

import time
import uuid
import logging
from typing import Dict, Any

from ..mcp.protocol import Tool, ToolParameter, ToolParameterType
from ..formatters import OutputFormat, TokenAwareFormatter
from ..logging_utils import RequestLogger
from ..jenkins.progressive import ProgressiveLogClient
from ..errors import InvalidParamsError


logger = logging.getLogger(__name__)


def register_log_tools(mcp_server, jenkins_adapter, config):
    """Register log-related tools."""

    log_client = ProgressiveLogClient(jenkins_adapter)

    # get_build_log
    async def get_log_handler(args: Dict[str, Any]) -> Dict[str, Any]:
        correlation_id = str(uuid.uuid4())
        start_time = time.time()

        with RequestLogger(logger, "get_build_log", correlation_id):
            job_name = args["name"]
            number_or_last = args.get("number", "last")
            start_byte = args.get("start", 0)
            max_bytes = args.get("max_bytes", config.log_max_bytes_default)
            filter_regex = args.get("filter_regex")
            redact = args.get("redact", True)
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

            # Get log summary
            summary = log_client.summarize_log(job_name, build_number, max_bytes)

            # Get log chunk if full format requested
            chunks = None
            if output_format == OutputFormat.FULL:
                chunk = log_client.get_log_chunk(
                    job_name, build_number, start=start_byte, max_bytes=max_bytes
                )

                # Apply filters
                text = chunk.text
                if filter_regex or redact:
                    text = log_client.filter_log(
                        text,
                        pattern=filter_regex,
                        redact=redact
                    )

                chunks = [{
                    "text": text,
                    "start": chunk.start,
                    "end": chunk.end,
                    "has_more": chunk.has_more
                }]

            # Format response
            result = TokenAwareFormatter.format_log_response(
                summary, chunks=chunks, format=output_format
            )

            result["build_number"] = build_number
            result["job_name"] = job_name

            took_ms = int((time.time() - start_time) * 1000)
            return TokenAwareFormatter.add_metadata(
                result, correlation_id, took_ms, output_format
            )

    mcp_server.register_tool(Tool(
        name="get_build_log",
        description="Get build log with smart truncation and filtering. Returns summary by default, full text on request.",
        parameters=[
            ToolParameter("name", ToolParameterType.STRING, "Full job name", required=True),
            ToolParameter("number", ToolParameterType.STRING, "Build number or 'last'", required=False, default="last"),
            ToolParameter("start", ToolParameterType.NUMBER, "Starting byte offset", required=False, default=0),
            ToolParameter("max_bytes", ToolParameterType.NUMBER, "Maximum bytes to retrieve", required=False),
            ToolParameter("filter_regex", ToolParameterType.STRING, "Regex pattern to filter log lines", required=False),
            ToolParameter("redact", ToolParameterType.BOOLEAN, "Remove ANSI codes and secret masks", required=False, default=True),
            ToolParameter("format", ToolParameterType.STRING, "Output format", required=False, default="summary", enum=["summary", "full"]),
        ],
        handler=get_log_handler
    ))

    # search_log
    async def search_log_handler(args: Dict[str, Any]) -> Dict[str, Any]:
        correlation_id = str(uuid.uuid4())
        start_time = time.time()

        with RequestLogger(logger, "search_log", correlation_id):
            job_name = args["name"]
            number_or_last = args.get("number", "last")
            pattern = args["pattern"]
            window_lines = args.get("window_lines", 5)
            max_bytes = args.get("max_bytes", config.log_max_bytes_default)

            # Get build number
            if number_or_last == "last":
                job_info = jenkins_adapter.get_job_info(job_name)
                last_build = job_info.get("lastBuild")
                if not last_build:
                    raise InvalidParamsError(f"Job '{job_name}' has no builds")
                build_number = last_build["number"]
            else:
                build_number = int(number_or_last)

            # Search log
            matches = log_client.search_log(
                job_name, build_number, pattern, window_lines, max_bytes
            )

            result = {
                "build_number": build_number,
                "job_name": job_name,
                "pattern": pattern,
                "matches_count": len(matches),
                "matches": [
                    {
                        "line_number": line_num,
                        "context": context[:500]  # Limit context size
                    }
                    for line_num, context in matches[:20]  # Top 20 matches
                ]
            }

            took_ms = int((time.time() - start_time) * 1000)
            return TokenAwareFormatter.add_metadata(
                result, correlation_id, took_ms, OutputFormat.SUMMARY
            )

    mcp_server.register_tool(Tool(
        name="search_log",
        description="Search build log for pattern and return matching lines with context",
        parameters=[
            ToolParameter("name", ToolParameterType.STRING, "Full job name", required=True),
            ToolParameter("number", ToolParameterType.STRING, "Build number or 'last'", required=False, default="last"),
            ToolParameter("pattern", ToolParameterType.STRING, "Regex pattern to search for", required=True),
            ToolParameter("window_lines", ToolParameterType.NUMBER, "Lines of context before/after match", required=False, default=5),
            ToolParameter("max_bytes", ToolParameterType.NUMBER, "Maximum bytes to search", required=False),
        ],
        handler=search_log_handler
    ))

    # tail_log_live (polling-based live tail)
    async def tail_log_live_handler(args: Dict[str, Any]) -> Dict[str, Any]:
        correlation_id = str(uuid.uuid4())
        start_time = time.time()

        with RequestLogger(logger, "tail_log_live", correlation_id):
            job_name = args["name"]
            build_number = int(args["build_number"])
            start_byte = args.get("start_byte", 0)
            max_bytes = args.get("max_bytes", config.log_max_bytes_default)

            # Get log chunk starting from start_byte
            chunk = log_client.get_log_chunk(
                job_name, build_number, start_byte, max_bytes
            )

            result = {
                "build_number": build_number,
                "job_name": job_name,
                "start_byte": start_byte,
                "next_byte": chunk.next_byte,
                "has_more": chunk.has_more,
                "log_content": chunk.text,
                "line_count": len(chunk.text.split("\n")) if chunk.text else 0,
            }

            took_ms = int((time.time() - start_time) * 1000)
            return TokenAwareFormatter.add_metadata(
                result, correlation_id, took_ms, OutputFormat.FULL
            )

    mcp_server.register_tool(Tool(
        name="tail_log_live",
        description="Get log chunk for live tailing (poll repeatedly with next_byte for streaming effect)",
        parameters=[
            ToolParameter("name", ToolParameterType.STRING, "Full job name", required=True),
            ToolParameter("build_number", ToolParameterType.NUMBER, "Build number", required=True),
            ToolParameter("start_byte", ToolParameterType.NUMBER, "Starting byte offset", required=False, default=0),
            ToolParameter("max_bytes", ToolParameterType.NUMBER, "Maximum bytes per chunk", required=False),
        ],
        handler=tail_log_live_handler
    ))
