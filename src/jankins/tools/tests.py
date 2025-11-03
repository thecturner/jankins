"""Test result analysis tools."""

import time
import uuid
import logging
from typing import Dict, Any

from ..mcp.protocol import Tool, ToolParameter, ToolParameterType
from ..formatters import OutputFormat, TokenAwareFormatter
from ..logging_utils import RequestLogger
from ..jenkins.testresults import TestResultParser
from ..errors import InvalidParamsError


logger = logging.getLogger(__name__)


def register_test_tools(mcp_server, jenkins_adapter, config):
    """Register test result analysis tools."""

    test_parser = TestResultParser(jenkins_adapter)

    # get_test_report
    async def get_test_report_handler(args: Dict[str, Any]) -> Dict[str, Any]:
        correlation_id = str(uuid.uuid4())
        start_time = time.time()

        with RequestLogger(logger, "get_test_report", correlation_id):
            job_name = args["name"]
            number_or_last = args.get("number", "last")
            detailed = args.get("detailed", False)
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

            # Get test report
            if detailed:
                report = test_parser.get_detailed_test_report(job_name, build_number)
            else:
                report = test_parser.get_test_report(job_name, build_number)

            if not report:
                result = {
                    "build_number": build_number,
                    "job_name": job_name,
                    "available": False,
                    "message": "No test results available for this build"
                }
            else:
                result = {
                    "build_number": build_number,
                    "job_name": job_name,
                    "available": True,
                    "total_tests": report.total_tests,
                    "passed": report.passed,
                    "failed": report.failed,
                    "skipped": report.skipped,
                    "errors": report.errors,
                    "pass_rate": round(report.pass_rate, 2),
                    "duration": round(report.duration, 2)
                }

                # Include detailed suites only in full format
                if output_format == OutputFormat.FULL and detailed and report.suites:
                    result["suites"] = [
                        {
                            "name": suite.name,
                            "tests": suite.tests,
                            "failures": suite.failures,
                            "errors": suite.errors,
                            "skipped": suite.skipped,
                            "duration": round(suite.duration, 2)
                        }
                        for suite in report.suites
                    ]

            took_ms = int((time.time() - start_time) * 1000)
            return TokenAwareFormatter.add_metadata(
                result, correlation_id, took_ms, output_format
            )

    mcp_server.register_tool(Tool(
        name="get_test_report",
        description="Get test results summary from a build (JUnit, pytest, etc.)",
        parameters=[
            ToolParameter("name", ToolParameterType.STRING, "Full job name", required=True),
            ToolParameter("number", ToolParameterType.STRING, "Build number or 'last'", required=False, default="last"),
            ToolParameter("detailed", ToolParameterType.BOOLEAN, "Include detailed test suites", required=False, default=False),
            ToolParameter("format", ToolParameterType.STRING, "Output format", required=False, default="summary", enum=["summary", "full"]),
        ],
        handler=get_test_report_handler
    ))

    # get_failed_tests
    async def get_failed_tests_handler(args: Dict[str, Any]) -> Dict[str, Any]:
        correlation_id = str(uuid.uuid4())
        start_time = time.time()

        with RequestLogger(logger, "get_failed_tests", correlation_id):
            job_name = args["name"]
            number_or_last = args.get("number", "last")
            limit = args.get("limit", 10)
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

            # Get failed tests
            failed_tests = test_parser.get_failed_tests(job_name, build_number, limit)

            result = {
                "build_number": build_number,
                "job_name": job_name,
                "failed_count": len(failed_tests),
                "failed_tests": []
            }

            for test in failed_tests:
                test_info = {
                    "name": test.name,
                    "class": test.class_name,
                    "duration": round(test.duration, 2),
                    "status": test.status,
                }

                # Include error details in full format
                if output_format == OutputFormat.FULL:
                    if test.error_message:
                        test_info["error_message"] = test.error_message
                    if test.error_stacktrace and len(test.error_stacktrace) < 2000:
                        test_info["stacktrace"] = test.error_stacktrace
                else:
                    # In summary mode, include truncated error message
                    if test.error_message:
                        test_info["error"] = test.error_message[:200]

                result["failed_tests"].append(test_info)

            took_ms = int((time.time() - start_time) * 1000)
            return TokenAwareFormatter.add_metadata(
                result, correlation_id, took_ms, output_format
            )

    mcp_server.register_tool(Tool(
        name="get_failed_tests",
        description="Get list of failed tests from a build with error details",
        parameters=[
            ToolParameter("name", ToolParameterType.STRING, "Full job name", required=True),
            ToolParameter("number", ToolParameterType.STRING, "Build number or 'last'", required=False, default="last"),
            ToolParameter("limit", ToolParameterType.NUMBER, "Maximum number of failed tests to return", required=False, default=10),
            ToolParameter("format", ToolParameterType.STRING, "Output format", required=False, default="summary", enum=["summary", "full"]),
        ],
        handler=get_failed_tests_handler
    ))

    # compare_test_results
    async def compare_test_results_handler(args: Dict[str, Any]) -> Dict[str, Any]:
        correlation_id = str(uuid.uuid4())
        start_time = time.time()

        with RequestLogger(logger, "compare_test_results", correlation_id):
            job_name = args["name"]
            base = int(args["base"])
            head = int(args["head"])
            format_str = args.get("format", "diff")
            output_format = OutputFormat(format_str)

            # Compare test results
            comparison = test_parser.compare_test_results(job_name, base, head)
            comparison["job_name"] = job_name

            took_ms = int((time.time() - start_time) * 1000)
            return TokenAwareFormatter.add_metadata(
                comparison, correlation_id, took_ms, output_format
            )

    mcp_server.register_tool(Tool(
        name="compare_test_results",
        description="Compare test results between two builds to identify new failures and regressions",
        parameters=[
            ToolParameter("name", ToolParameterType.STRING, "Full job name", required=True),
            ToolParameter("base", ToolParameterType.STRING, "Base build number", required=True),
            ToolParameter("head", ToolParameterType.STRING, "Head build number to compare", required=True),
            ToolParameter("format", ToolParameterType.STRING, "Output format", required=False, default="diff", enum=["summary", "full", "diff"]),
        ],
        handler=compare_test_results_handler
    ))

    # detect_flaky_tests
    async def detect_flaky_tests_handler(args: Dict[str, Any]) -> Dict[str, Any]:
        correlation_id = str(uuid.uuid4())
        start_time = time.time()

        with RequestLogger(logger, "detect_flaky_tests", correlation_id):
            job_name = args["name"]
            build_count = args.get("build_count", 10)
            format_str = args.get("format", "summary")
            output_format = OutputFormat(format_str)

            # Get last N builds
            job_info = jenkins_adapter.get_job_info(job_name)
            builds = job_info.get("builds", [])[:build_count]
            build_numbers = [b["number"] for b in builds]

            if not build_numbers:
                result = {
                    "job_name": job_name,
                    "builds_analyzed": 0,
                    "flaky_tests": []
                }
            else:
                # Detect flaky tests
                flaky_tests = test_parser.get_flaky_tests(job_name, build_numbers)

                result = {
                    "job_name": job_name,
                    "builds_analyzed": len(build_numbers),
                    "build_range": f"{build_numbers[-1]}-{build_numbers[0]}",
                    "flaky_count": len(flaky_tests),
                    "flaky_tests": flaky_tests[:20]  # Top 20
                }

                # In summary mode, exclude detailed statuses
                if output_format == OutputFormat.SUMMARY:
                    for test in result["flaky_tests"]:
                        test.pop("statuses", None)

            took_ms = int((time.time() - start_time) * 1000)
            return TokenAwareFormatter.add_metadata(
                result, correlation_id, took_ms, output_format
            )

    mcp_server.register_tool(Tool(
        name="detect_flaky_tests",
        description="Identify flaky tests (inconsistent pass/fail) across recent builds",
        parameters=[
            ToolParameter("name", ToolParameterType.STRING, "Full job name", required=True),
            ToolParameter("build_count", ToolParameterType.NUMBER, "Number of recent builds to analyze", required=False, default=10),
            ToolParameter("format", ToolParameterType.STRING, "Output format", required=False, default="summary", enum=["summary", "full"]),
        ],
        handler=detect_flaky_tests_handler
    ))
