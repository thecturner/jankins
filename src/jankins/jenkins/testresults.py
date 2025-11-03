"""Test result parsing for JUnit, pytest, and other test frameworks.

Parses test reports from Jenkins builds to provide detailed test analysis.
"""

import logging
import xml.etree.ElementTree as ET
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class TestCase:
    """Represents a single test case result."""
    name: str
    class_name: str
    duration: float
    status: str  # PASSED, FAILED, SKIPPED, ERROR
    error_message: Optional[str] = None
    error_type: Optional[str] = None
    error_stacktrace: Optional[str] = None


@dataclass
class TestSuite:
    """Represents a test suite (collection of test cases)."""
    name: str
    tests: int
    failures: int
    errors: int
    skipped: int
    duration: float
    test_cases: List[TestCase]


@dataclass
class TestReport:
    """Represents complete test report from a build."""
    total_tests: int
    passed: int
    failed: int
    skipped: int
    errors: int
    duration: float
    suites: List[TestSuite]

    @property
    def pass_rate(self) -> float:
        """Calculate pass rate percentage."""
        if self.total_tests == 0:
            return 0.0
        return (self.passed / self.total_tests) * 100


class TestResultParser:
    """Parser for various test result formats."""

    def __init__(self, jenkins_adapter):
        """Initialize test result parser.

        Args:
            jenkins_adapter: JenkinsAdapter instance for API calls
        """
        self.adapter = jenkins_adapter

    def get_test_report(
        self, job_name: str, build_number: int
    ) -> Optional[TestReport]:
        """Get test report from Jenkins test results API.

        Args:
            job_name: Full job name
            build_number: Build number

        Returns:
            TestReport or None if no test results available
        """
        try:
            # Get test report via Jenkins API
            build_info = self.adapter.get_build_info(job_name, build_number)

            # Check if test results are available
            actions = build_info.get("actions", [])
            test_action = None

            for action in actions:
                if action and action.get("_class") in [
                    "hudson.tasks.junit.TestResultAction",
                    "hudson.tasks.test.AggregatedTestResultAction"
                ]:
                    test_action = action
                    break

            if not test_action:
                logger.debug(f"No test results found for {job_name} #{build_number}")
                return None

            # Parse test results
            total = test_action.get("totalCount", 0)
            failed = test_action.get("failCount", 0)
            skipped = test_action.get("skipCount", 0)

            return TestReport(
                total_tests=total,
                passed=total - failed - skipped,
                failed=failed,
                skipped=skipped,
                errors=0,  # Jenkins doesn't separate errors from failures
                duration=0.0,  # Not available in summary
                suites=[]  # Summary mode doesn't include detailed suites
            )

        except Exception as e:
            logger.warning(f"Failed to get test report: {e}")
            return None

    def get_detailed_test_report(
        self, job_name: str, build_number: int
    ) -> Optional[TestReport]:
        """Get detailed test report with individual test cases.

        Args:
            job_name: Full job name
            build_number: Build number

        Returns:
            Detailed TestReport with test suites and cases
        """
        try:
            # Get detailed test results via testReport API
            path = f"/job/{job_name}/{build_number}/testReport/api/json"
            response = self.adapter.rest_get(path, params={"tree": "suites[name,duration,cases[name,className,duration,status,errorDetails,errorStackTrace]]"})
            data = response.json()

            suites = []
            total_tests = 0
            total_passed = 0
            total_failed = 0
            total_skipped = 0
            total_errors = 0
            total_duration = 0.0

            for suite_data in data.get("suites", []):
                test_cases = []
                suite_tests = 0
                suite_failures = 0
                suite_errors = 0
                suite_skipped = 0

                for case_data in suite_data.get("cases", []):
                    status = case_data.get("status", "UNKNOWN")
                    duration = case_data.get("duration", 0.0)

                    test_case = TestCase(
                        name=case_data.get("name", ""),
                        class_name=case_data.get("className", ""),
                        duration=duration,
                        status=status,
                        error_message=case_data.get("errorDetails"),
                        error_type=None,  # Not provided by Jenkins API
                        error_stacktrace=case_data.get("errorStackTrace")
                    )

                    test_cases.append(test_case)
                    suite_tests += 1

                    if status == "FAILED":
                        suite_failures += 1
                    elif status == "SKIPPED":
                        suite_skipped += 1
                    elif status == "PASSED":
                        pass
                    else:
                        suite_errors += 1

                suite = TestSuite(
                    name=suite_data.get("name", "Unknown"),
                    tests=suite_tests,
                    failures=suite_failures,
                    errors=suite_errors,
                    skipped=suite_skipped,
                    duration=suite_data.get("duration", 0.0),
                    test_cases=test_cases
                )

                suites.append(suite)
                total_tests += suite_tests
                total_failed += suite_failures
                total_errors += suite_errors
                total_skipped += suite_skipped
                total_duration += suite.duration

            total_passed = total_tests - total_failed - total_errors - total_skipped

            return TestReport(
                total_tests=total_tests,
                passed=total_passed,
                failed=total_failed,
                skipped=total_skipped,
                errors=total_errors,
                duration=total_duration,
                suites=suites
            )

        except Exception as e:
            logger.warning(f"Failed to get detailed test report: {e}")
            return None

    def get_failed_tests(
        self, job_name: str, build_number: int, limit: int = 10
    ) -> List[TestCase]:
        """Get only failed test cases from a build.

        Args:
            job_name: Full job name
            build_number: Build number
            limit: Maximum number of failed tests to return

        Returns:
            List of failed TestCase objects
        """
        report = self.get_detailed_test_report(job_name, build_number)
        if not report:
            return []

        failed_tests = []
        for suite in report.suites:
            for test_case in suite.test_cases:
                if test_case.status in ("FAILED", "ERROR"):
                    failed_tests.append(test_case)
                    if len(failed_tests) >= limit:
                        return failed_tests

        return failed_tests

    def compare_test_results(
        self, job_name: str, base_build: int, head_build: int
    ) -> Dict[str, Any]:
        """Compare test results between two builds.

        Args:
            job_name: Full job name
            base_build: Base build number
            head_build: Head build number

        Returns:
            Comparison data with new failures and regressions
        """
        base_report = self.get_test_report(job_name, base_build)
        head_report = self.get_test_report(job_name, head_build)

        if not base_report or not head_report:
            return {
                "available": False,
                "error": "Test results not available for comparison"
            }

        # Calculate differences
        test_delta = head_report.total_tests - base_report.total_tests
        failed_delta = head_report.failed - base_report.failed
        pass_rate_delta = head_report.pass_rate - base_report.pass_rate

        return {
            "available": True,
            "base_build": base_build,
            "head_build": head_build,
            "base_stats": {
                "total": base_report.total_tests,
                "passed": base_report.passed,
                "failed": base_report.failed,
                "skipped": base_report.skipped,
                "pass_rate": round(base_report.pass_rate, 2)
            },
            "head_stats": {
                "total": head_report.total_tests,
                "passed": head_report.passed,
                "failed": head_report.failed,
                "skipped": head_report.skipped,
                "pass_rate": round(head_report.pass_rate, 2)
            },
            "deltas": {
                "tests": test_delta,
                "failed": failed_delta,
                "pass_rate": round(pass_rate_delta, 2)
            },
            "regression": failed_delta > 0,
            "improvement": failed_delta < 0
        }

    def get_flaky_tests(
        self, job_name: str, build_numbers: List[int]
    ) -> List[Dict[str, Any]]:
        """Identify flaky tests across multiple builds.

        A test is considered flaky if it has inconsistent results
        (passes in some builds, fails in others).

        Args:
            job_name: Full job name
            build_numbers: List of build numbers to analyze

        Returns:
            List of flaky tests with failure rate
        """
        # Track test results across builds
        test_results: Dict[str, List[str]] = {}

        for build_num in build_numbers:
            report = self.get_detailed_test_report(job_name, build_num)
            if not report:
                continue

            for suite in report.suites:
                for test_case in suite.test_cases:
                    test_key = f"{test_case.class_name}.{test_case.name}"
                    if test_key not in test_results:
                        test_results[test_key] = []
                    test_results[test_key].append(test_case.status)

        # Identify flaky tests (have both PASSED and FAILED statuses)
        flaky = []
        for test_name, statuses in test_results.items():
            if len(set(statuses)) > 1 and "FAILED" in statuses and "PASSED" in statuses:
                failure_count = statuses.count("FAILED")
                total_runs = len(statuses)
                failure_rate = (failure_count / total_runs) * 100

                flaky.append({
                    "test": test_name,
                    "failure_count": failure_count,
                    "total_runs": total_runs,
                    "failure_rate": round(failure_rate, 2),
                    "statuses": statuses
                })

        # Sort by failure rate descending
        flaky.sort(key=lambda x: x["failure_rate"], reverse=True)
        return flaky
