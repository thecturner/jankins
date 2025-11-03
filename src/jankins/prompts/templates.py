"""Prompt templates for common Jenkins workflows.

These prompts help users accomplish common CI/CD tasks by combining
multiple tool calls with helpful context.
"""

import logging
from typing import Dict, Any, List

from ..mcp.protocol import Prompt, ToolParameter, ToolParameterType


logger = logging.getLogger(__name__)


def register_prompts(mcp_server, jenkins_adapter, config):
    """Register prompt templates with the MCP server."""

    # investigate_failure
    async def investigate_failure_handler(args: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Prompt for investigating a failing pipeline."""
        job = args["job"]
        build = args.get("build", "last")

        messages = [
            {
                "role": "user",
                "content": {
                    "type": "text",
                    "text": f"""I need to investigate a failing Jenkins build.

Job: {job}
Build: #{build}

Please help me:
1. Get the build status and basic information
2. Retrieve a summary of the build log focusing on errors
3. Perform failure triage to identify root causes
4. Provide recommended next steps for fixing the issue

Use the following tools:
- get_build to get build information
- get_build_log with format=summary to get error summary
- triage_failure to analyze the failure
- get_build_changes to see recent commits that may have caused the failure
"""
                }
            }
        ]

        return messages

    mcp_server.register_prompt(Prompt(
        name="investigate_failure",
        description="Investigate a failing pipeline step with root cause analysis",
        arguments=[
            ToolParameter("job", ToolParameterType.STRING, "Job name", required=True),
            ToolParameter("build", ToolParameterType.STRING, "Build number or 'last'", required=False),
        ],
        handler=investigate_failure_handler
    ))

    # tail_errors
    async def tail_errors_handler(args: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Prompt for tailing only warnings and errors."""
        job = args["job"]
        build = args.get("build", "last")

        messages = [
            {
                "role": "user",
                "content": {
                    "type": "text",
                    "text": f"""Show me only the warnings and errors from a build.

Job: {job}
Build: #{build}

Please use get_build_log with:
- filter_regex to match lines containing ERROR or WARN
- redact=true to clean up ANSI codes
- format=summary for a compact view

Focus on the most recent errors at the end of the log.
"""
                }
            }
        ]

        return messages

    mcp_server.register_prompt(Prompt(
        name="tail_errors",
        description="Tail only warnings and errors for the last run",
        arguments=[
            ToolParameter("job", ToolParameterType.STRING, "Job name", required=True),
            ToolParameter("build", ToolParameterType.STRING, "Build number or 'last'", required=False),
        ],
        handler=tail_errors_handler
    ))

    # compare_builds
    async def compare_builds_handler(args: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Prompt for comparing two builds."""
        job = args["job"]
        base = args["base"]
        head = args["head"]

        messages = [
            {
                "role": "user",
                "content": {
                    "type": "text",
                    "text": f"""Compare two builds to understand what changed.

Job: {job}
Base build: #{base}
Head build: #{head}

Please use:
- compare_runs to see differences in duration and results
- get_build_changes for both builds to see commit differences
- If results differ, use triage_failure on the failing build

Summarize key differences and potential causes of any new failures.
"""
                }
            }
        ]

        return messages

    mcp_server.register_prompt(Prompt(
        name="compare_builds",
        description="Compare two builds to identify differences",
        arguments=[
            ToolParameter("job", ToolParameterType.STRING, "Job name", required=True),
            ToolParameter("base", ToolParameterType.STRING, "Base build number", required=True),
            ToolParameter("head", ToolParameterType.STRING, "Head build number", required=True),
        ],
        handler=compare_builds_handler
    ))

    # check_job_health
    async def check_job_health_handler(args: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Prompt for checking job health."""
        job = args["job"]

        messages = [
            {
                "role": "user",
                "content": {
                    "type": "text",
                    "text": f"""Check the overall health of a Jenkins job.

Job: {job}

Please:
1. Get job information including health reports and build history
2. Check the last successful build and last failed build
3. If there are recent failures, investigate the most recent one
4. Provide a summary of job health and stability

Use:
- get_job to get job details and health reports
- get_build for last successful and last failed builds
- triage_failure if recent builds are failing
"""
                }
            }
        ]

        return messages

    mcp_server.register_prompt(Prompt(
        name="check_job_health",
        description="Check overall health and stability of a job",
        arguments=[
            ToolParameter("job", ToolParameterType.STRING, "Job name", required=True),
        ],
        handler=check_job_health_handler
    ))

    # trigger_with_params
    async def trigger_with_params_handler(args: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Prompt for triggering a parameterized build."""
        job = args["job"]
        params_desc = args.get("parameters", "default parameters")

        messages = [
            {
                "role": "user",
                "content": {
                    "type": "text",
                    "text": f"""Trigger a new build for a Jenkins job.

Job: {job}
Parameters: {params_desc}

Please:
1. Get job information to understand what parameters are available
2. Trigger the build with the specified parameters
3. Monitor the queue to confirm the build is scheduled

Use:
- get_job to see job configuration and parameters
- trigger_build with appropriate parameters
- summarize_queue to check build was queued
"""
                }
            }
        ]

        return messages

    mcp_server.register_prompt(Prompt(
        name="trigger_with_params",
        description="Trigger a parameterized build with guidance",
        arguments=[
            ToolParameter("job", ToolParameterType.STRING, "Job name", required=True),
            ToolParameter("parameters", ToolParameterType.STRING, "Description of parameters to use", required=False),
        ],
        handler=trigger_with_params_handler
    ))

    # search_logs
    async def search_logs_handler(args: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Prompt for searching logs for a pattern."""
        job = args["job"]
        pattern = args["pattern"]
        build = args.get("build", "last")

        messages = [
            {
                "role": "user",
                "content": {
                    "type": "text",
                    "text": f"""Search build logs for a specific pattern.

Job: {job}
Build: #{build}
Pattern: {pattern}

Please use search_log to find all occurrences of the pattern with context.
Show the matching lines and their context to help understand where and why
the pattern appears in the build log.
"""
                }
            }
        ]

        return messages

    mcp_server.register_prompt(Prompt(
        name="search_logs",
        description="Search build logs for a specific pattern or error",
        arguments=[
            ToolParameter("job", ToolParameterType.STRING, "Job name", required=True),
            ToolParameter("pattern", ToolParameterType.STRING, "Pattern to search for (regex)", required=True),
            ToolParameter("build", ToolParameterType.STRING, "Build number or 'last'", required=False),
        ],
        handler=search_logs_handler
    ))
