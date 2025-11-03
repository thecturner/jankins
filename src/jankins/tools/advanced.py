"""Advanced analysis tools for failure triage and comparison."""

import time
import uuid
import logging
import re
from typing import Dict, Any, List

from ..mcp.protocol import Tool, ToolParameter, ToolParameterType
from ..formatters import OutputFormat, TokenAwareFormatter
from ..logging_utils import RequestLogger
from ..jenkins.progressive import ProgressiveLogClient
from ..jenkins.blueocean import BlueOceanClient
from ..analyzers import get_analyzer, MavenAnalyzer, GradleAnalyzer, NpmAnalyzer
from ..errors import InvalidParamsError


logger = logging.getLogger(__name__)


def register_advanced_tools(mcp_server, jenkins_adapter, config):
    """Register advanced analysis tools."""

    log_client = ProgressiveLogClient(jenkins_adapter)
    blue_ocean_client = BlueOceanClient(jenkins_adapter)

    # triage_failure
    async def triage_failure_handler(args: Dict[str, Any]) -> Dict[str, Any]:
        correlation_id = str(uuid.uuid4())
        start_time = time.time()

        with RequestLogger(logger, "triage_failure", correlation_id):
            job_name = args["name"]
            number_or_last = args.get("number", "last")
            max_bytes = args.get("max_bytes", config.log_max_bytes_default)
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

            # Get build info and log summary
            build_info = jenkins_adapter.get_build_info(job_name, build_number)
            log_summary = log_client.summarize_log(job_name, build_number, max_bytes)

            # Analyze failure
            result = build_info.get("result")
            if result != "FAILURE":
                result_data = {
                    "build_number": build_number,
                    "result": result,
                    "message": f"Build is not a failure (result: {result})",
                    "hypotheses": [],
                    "top_errors": [],
                    "failing_stages": [],
                    "next_steps": []
                }
            else:
                # Generate hypotheses based on error patterns
                hypotheses = _generate_hypotheses(log_summary.last_error_lines)

                # Get suspect changes
                changes = build_info.get("changeSet", {}).get("items", [])
                suspect_changes = [
                    {
                        "commit": c.get("commitId", "")[:8],
                        "author": c.get("author", {}).get("fullName", "Unknown"),
                        "message": c.get("msg", "")[:100]
                    }
                    for c in changes[:5]
                ]

                # Generate next steps
                next_steps = _generate_next_steps(
                    log_summary.failing_stages,
                    log_summary.last_error_lines,
                    len(changes) > 0
                )

                result_data = {
                    "build_number": build_number,
                    "result": result,
                    "hypotheses": hypotheses,
                    "top_errors": log_summary.last_error_lines,
                    "failing_stages": log_summary.failing_stages,
                    "suspect_changes": suspect_changes,
                    "next_steps": next_steps
                }

                # Format using TokenAwareFormatter
                result_data = TokenAwareFormatter.format_triage(
                    hypotheses=hypotheses,
                    top_errors=log_summary.last_error_lines,
                    failing_stages=log_summary.failing_stages,
                    suspect_changes=suspect_changes,
                    next_steps=next_steps,
                    format=output_format
                )
                result_data["build_number"] = build_number
                result_data["job_name"] = job_name

            took_ms = int((time.time() - start_time) * 1000)
            return TokenAwareFormatter.add_metadata(
                result_data, correlation_id, took_ms, output_format
            )

    mcp_server.register_tool(Tool(
        name="triage_failure",
        description="Analyze a failed build and provide root cause hypotheses and next steps",
        parameters=[
            ToolParameter("name", ToolParameterType.STRING, "Full job name", required=True),
            ToolParameter("number", ToolParameterType.STRING, "Build number or 'last'", required=False, default="last"),
            ToolParameter("max_bytes", ToolParameterType.NUMBER, "Maximum log bytes to analyze", required=False),
            ToolParameter("format", ToolParameterType.STRING, "Output format", required=False, default="summary", enum=["summary", "full"]),
        ],
        handler=triage_failure_handler
    ))

    # compare_runs
    async def compare_runs_handler(args: Dict[str, Any]) -> Dict[str, Any]:
        correlation_id = str(uuid.uuid4())
        start_time = time.time()

        with RequestLogger(logger, "compare_runs", correlation_id):
            job_name = args["name"]
            base = args["base"]
            head = args["head"]
            format_str = args.get("format", "diff")
            output_format = OutputFormat(format_str)

            # Get both builds
            base_build = jenkins_adapter.get_build_info(job_name, int(base))
            head_build = jenkins_adapter.get_build_info(job_name, int(head))

            # Calculate duration delta
            duration_delta = head_build.get("duration", 0) - base_build.get("duration", 0)

            # Compare results
            result_changed = base_build.get("result") != head_build.get("result")

            # Stage comparison with Blue Ocean API
            try:
                comparison = blue_ocean_client.compare_pipeline_runs(
                    job_name, int(base), int(head)
                )
                stage_diffs = comparison.get("stage_diffs", [])
            except Exception as e:
                logger.debug(f"Blue Ocean comparison not available: {e}")
                stage_diffs = []

            # Format comparison
            result = TokenAwareFormatter.format_comparison(
                base_build=base_build,
                head_build=head_build,
                duration_delta=duration_delta,
                stage_diffs=stage_diffs,
                format=output_format
            )

            result["job_name"] = job_name

            took_ms = int((time.time() - start_time) * 1000)
            return TokenAwareFormatter.add_metadata(
                result, correlation_id, took_ms, output_format
            )

    mcp_server.register_tool(Tool(
        name="compare_runs",
        description="Compare two builds to identify differences in duration, stages, and results",
        parameters=[
            ToolParameter("name", ToolParameterType.STRING, "Full job name", required=True),
            ToolParameter("base", ToolParameterType.STRING, "Base build number", required=True),
            ToolParameter("head", ToolParameterType.STRING, "Head build number to compare", required=True),
            ToolParameter("format", ToolParameterType.STRING, "Output format", required=False, default="diff", enum=["summary", "full", "diff"]),
        ],
        handler=compare_runs_handler
    ))

    # get_pipeline_graph
    async def get_pipeline_graph_handler(args: Dict[str, Any]) -> Dict[str, Any]:
        correlation_id = str(uuid.uuid4())
        start_time = time.time()

        with RequestLogger(logger, "get_pipeline_graph", correlation_id):
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

            # Get pipeline graph from Blue Ocean
            try:
                graph = blue_ocean_client.get_pipeline_graph(job_name, build_number)
                failing_stages = blue_ocean_client.get_failing_stages_detailed(
                    job_name, build_number
                )

                result = {
                    "build_number": build_number,
                    "job_name": job_name,
                    "stages": graph.get("stages", []),
                    "parallel_stages": graph.get("parallel_stages", []),
                    "total_duration_ms": graph.get("total_duration_ms", 0),
                    "node_count": graph.get("node_count", 0),
                    "failing_stages": failing_stages,
                }

                # In summary mode, simplify the output
                if output_format == OutputFormat.SUMMARY:
                    result["stages"] = [
                        {
                            "name": s["name"],
                            "result": s["result"],
                            "duration_ms": s["duration_ms"]
                        }
                        for s in result["stages"]
                    ]
                    if result["parallel_stages"]:
                        result["parallel_stages"] = [
                            [{"name": s["name"], "result": s["result"]} for s in group]
                            for group in result["parallel_stages"]
                        ]

            except Exception as e:
                logger.warning(f"Blue Ocean API not available: {e}")
                result = {
                    "build_number": build_number,
                    "job_name": job_name,
                    "error": "Blue Ocean API not available for this build",
                    "stages": [],
                    "available": False
                }

            took_ms = int((time.time() - start_time) * 1000)
            return TokenAwareFormatter.add_metadata(
                result, correlation_id, took_ms, output_format
            )

    mcp_server.register_tool(Tool(
        name="get_pipeline_graph",
        description="Get pipeline execution graph with stages, parallel branches, and timing (requires Blue Ocean plugin)",
        parameters=[
            ToolParameter("name", ToolParameterType.STRING, "Full job name", required=True),
            ToolParameter("number", ToolParameterType.STRING, "Build number or 'last'", required=False, default="last"),
            ToolParameter("format", ToolParameterType.STRING, "Output format", required=False, default="summary", enum=["summary", "full"]),
        ],
        handler=get_pipeline_graph_handler
    ))

    # analyze_build_log
    async def analyze_build_log_handler(args: Dict[str, Any]) -> Dict[str, Any]:
        correlation_id = str(uuid.uuid4())
        start_time = time.time()

        with RequestLogger(logger, "analyze_build_log", correlation_id):
            job_name = args["name"]
            number_or_last = args.get("number", "last")
            build_tool = args.get("build_tool")
            max_bytes = args.get("max_bytes", config.log_max_bytes_default)
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

            # Get log content
            log_summary = log_client.summarize_log(job_name, build_number, max_bytes)
            log_content = "\n".join(log_summary.last_error_lines)

            # Get more context if needed
            if len(log_content) < 1000:
                # Get more log content for better analysis
                try:
                    full_log = jenkins_adapter.get_build_console_output(job_name, build_number)
                    # Use last 50KB for analysis
                    log_content = full_log[-50000:] if len(full_log) > 50000 else full_log
                except Exception as e:
                    logger.debug(f"Could not get full log: {e}")

            # Auto-detect build tool if not specified
            if not build_tool:
                # Try each analyzer
                for analyzer_class in [MavenAnalyzer, GradleAnalyzer, NpmAnalyzer]:
                    analyzer = analyzer_class()
                    if analyzer.detect(log_content):
                        build_tool = analyzer.tool_name
                        break

            # Analyze with appropriate analyzer
            if build_tool:
                try:
                    analyzer = get_analyzer(build_tool)
                    analysis = analyzer.analyze(log_content)

                    result = {
                        "build_number": build_number,
                        "job_name": job_name,
                        "build_tool": analysis.build_tool,
                        "detected": analysis.detected,
                        "summary": analysis.summary,
                        "compilation_errors": analysis.compilation_errors,
                        "test_failures": analysis.test_failures,
                        "issues": analysis.issues,
                        "recommendations": analysis.recommendations,
                    }

                    # Include detailed errors/warnings in full format
                    if output_format == OutputFormat.FULL:
                        result["errors"] = analysis.errors[:10]
                        result["warnings"] = analysis.warnings[:10]
                        result["dependencies_failed"] = analysis.dependencies_failed
                    else:
                        result["error_count"] = len(analysis.errors)
                        result["warning_count"] = len(analysis.warnings)

                except ValueError as e:
                    result = {
                        "build_number": build_number,
                        "job_name": job_name,
                        "error": str(e)
                    }
            else:
                result = {
                    "build_number": build_number,
                    "job_name": job_name,
                    "error": "Could not detect build tool (maven, gradle, npm)",
                    "hint": "Specify build_tool parameter explicitly"
                }

            took_ms = int((time.time() - start_time) * 1000)
            return TokenAwareFormatter.add_metadata(
                result, correlation_id, took_ms, output_format
            )

    mcp_server.register_tool(Tool(
        name="analyze_build_log",
        description="Analyze build logs with build tool-specific parsers (Maven, Gradle, NPM) for detailed error analysis",
        parameters=[
            ToolParameter("name", ToolParameterType.STRING, "Full job name", required=True),
            ToolParameter("number", ToolParameterType.STRING, "Build number or 'last'", required=False, default="last"),
            ToolParameter("build_tool", ToolParameterType.STRING, "Build tool (maven, gradle, npm) or auto-detect", required=False),
            ToolParameter("max_bytes", ToolParameterType.NUMBER, "Maximum log bytes to analyze", required=False),
            ToolParameter("format", ToolParameterType.STRING, "Output format", required=False, default="summary", enum=["summary", "full"]),
        ],
        handler=analyze_build_log_handler
    ))

    # retry_flaky_build
    async def retry_flaky_build_handler(args: Dict[str, Any]) -> Dict[str, Any]:
        correlation_id = str(uuid.uuid4())
        start_time = time.time()

        with RequestLogger(logger, "retry_flaky_build", correlation_id):
            job_name = args["name"]
            max_retries = args.get("max_retries", 3)
            delay_seconds = args.get("delay_seconds", 5)
            parameters = args.get("parameters", {})
            format_str = args.get("format", "summary")
            output_format = OutputFormat(format_str)

            retries = []
            success = False

            for attempt in range(1, max_retries + 1):
                logger.info(f"Retry attempt {attempt}/{max_retries} for {job_name}")

                # Trigger build
                try:
                    queue_id = jenkins_adapter.build_job(job_name, parameters)

                    # Wait a bit for build to start
                    import asyncio
                    await asyncio.sleep(delay_seconds)

                    # Get latest build info
                    job_info = jenkins_adapter.get_job_info(job_name)
                    last_build = job_info.get("lastBuild")

                    if last_build:
                        build_number = last_build["number"]
                        build_info = jenkins_adapter.get_build_info(job_name, build_number)
                        result_status = build_info.get("result", "UNKNOWN")

                        retries.append({
                            "attempt": attempt,
                            "build_number": build_number,
                            "result": result_status,
                            "queue_id": queue_id
                        })

                        if result_status == "SUCCESS":
                            success = True
                            break

                except Exception as e:
                    logger.error(f"Retry attempt {attempt} failed: {e}")
                    retries.append({
                        "attempt": attempt,
                        "error": str(e)
                    })

                # Wait before next retry
                if attempt < max_retries:
                    await asyncio.sleep(delay_seconds)

            result = {
                "job_name": job_name,
                "success": success,
                "attempts": len(retries),
                "max_retries": max_retries,
                "retries": retries
            }

            if success:
                result["message"] = f"Build succeeded after {len(retries)} attempt(s)"
            else:
                result["message"] = f"Build failed after {len(retries)} attempt(s)"

            took_ms = int((time.time() - start_time) * 1000)
            return TokenAwareFormatter.add_metadata(
                result, correlation_id, took_ms, output_format
            )

    mcp_server.register_tool(Tool(
        name="retry_flaky_build",
        description="Retry a flaky build multiple times until it succeeds or max retries reached",
        parameters=[
            ToolParameter("name", ToolParameterType.STRING, "Full job name", required=True),
            ToolParameter("max_retries", ToolParameterType.NUMBER, "Maximum retry attempts", required=False, default=3),
            ToolParameter("delay_seconds", ToolParameterType.NUMBER, "Delay between retries in seconds", required=False, default=5),
            ToolParameter("parameters", ToolParameterType.OBJECT, "Build parameters", required=False),
            ToolParameter("format", ToolParameterType.STRING, "Output format", required=False, default="summary", enum=["summary", "full"]),
        ],
        handler=retry_flaky_build_handler
    ))


def _generate_hypotheses(error_lines: List[str]) -> List[str]:
    """Generate failure hypotheses based on error patterns."""
    hypotheses = []

    # Join all error lines for pattern matching
    all_errors = " ".join(error_lines).lower()

    # Common error patterns
    if "timeout" in all_errors or "timed out" in all_errors:
        hypotheses.append("Timeout: Operation exceeded time limit")

    if "out of memory" in all_errors or "oom" in all_errors:
        hypotheses.append("Out of Memory: Insufficient heap or memory allocation")

    if "connection refused" in all_errors or "connection reset" in all_errors:
        hypotheses.append("Network Issue: Connection to external service failed")

    if "permission denied" in all_errors or "forbidden" in all_errors:
        hypotheses.append("Permission Issue: Insufficient access rights")

    if "no such file" in all_errors or "not found" in all_errors:
        hypotheses.append("Missing Resource: Required file or dependency not found")

    if "compilation error" in all_errors or "syntax error" in all_errors:
        hypotheses.append("Code Error: Compilation or syntax issue in source")

    if "test" in all_errors and ("fail" in all_errors or "error" in all_errors):
        hypotheses.append("Test Failure: One or more tests did not pass")

    if "npm" in all_errors or "yarn" in all_errors or "package" in all_errors:
        hypotheses.append("Dependency Issue: Package installation or resolution failed")

    if not hypotheses:
        hypotheses.append("Unknown: Review error logs for specific failure patterns")

    return hypotheses[:5]  # Top 5


def _generate_next_steps(
    failing_stages: List[str],
    error_lines: List[str],
    has_changes: bool
) -> List[str]:
    """Generate recommended next steps for failure investigation."""
    steps = []

    if failing_stages:
        steps.append(f"Review failing stage(s): {', '.join(failing_stages[:3])}")

    if error_lines:
        steps.append("Examine error messages in build log for root cause")

    if has_changes:
        steps.append("Review recent commits for potentially breaking changes")

    steps.append("Check if issue reproduces locally with same configuration")

    steps.append("Compare with last successful build for environmental differences")

    all_errors = " ".join(error_lines).lower()
    if "test" in all_errors:
        steps.append("Run failing tests locally to debug")

    if "timeout" in all_errors:
        steps.append("Increase timeout limits or optimize slow operations")

    if "memory" in all_errors:
        steps.append("Increase memory allocation or check for memory leaks")

    return steps[:7]  # Top 7
