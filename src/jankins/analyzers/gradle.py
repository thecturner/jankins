"""Gradle build log analyzer."""

import re
from typing import List
from .base import LogAnalyzer, AnalysisResult


class GradleAnalyzer(LogAnalyzer):
    """Analyzer for Gradle builds."""

    @property
    def tool_name(self) -> str:
        return "gradle"

    @property
    def detection_patterns(self) -> List[str]:
        return [
            r"Gradle \d+\.\d+",
            r"gradle (build|test|assemble|clean)",
            r"> Task :",
            r"BUILD SUCCESSFUL in",
            r"BUILD FAILED in",
        ]

    def analyze(self, log_content: str) -> AnalysisResult:
        """Analyze Gradle build log.

        Args:
            log_content: Gradle build log

        Returns:
            AnalysisResult with Gradle-specific information
        """
        result = AnalysisResult(
            build_tool="gradle",
            detected=self.detect(log_content)
        )

        if not result.detected:
            result.summary = "Gradle build not detected in log"
            return result

        # Extract errors
        error_patterns = [
            r"FAILURE: .*",
            r"\* What went wrong:.*",
            r"Execution failed for task .*",
            r"Could not resolve .*",
            r"> Compilation failed.*",
        ]
        result.errors = self.extract_errors(log_content, error_patterns)

        # Extract warnings
        warning_patterns = [
            r"warning: .*",
            r"deprecated: .*",
        ]
        result.warnings = self.extract_warnings(log_content, warning_patterns)

        # Parse compilation errors
        compilation_pattern = r"(\d+) error[s]?"
        compilation_matches = re.findall(compilation_pattern, log_content)
        if compilation_matches:
            result.compilation_errors = sum(int(m) for m in compilation_matches)

        # Parse test failures
        test_failure_pattern = r"(\d+) tests? completed, (\d+) failed"
        test_matches = re.findall(test_failure_pattern, log_content)
        if test_matches:
            result.test_failures = sum(int(failed) for _, failed in test_matches)

        # Extract failed dependencies
        dep_pattern = r"Could not resolve ([\w\.\-:]+)"
        result.dependencies_failed = list(set(re.findall(dep_pattern, log_content)))

        # Parse specific issues
        result.issues = self._parse_gradle_issues(log_content)

        # Generate recommendations
        result.recommendations = self._generate_recommendations(result)

        # Generate summary
        result.summary = self._generate_summary(result)

        return result

    def _parse_gradle_issues(self, log_content: str) -> List[dict]:
        """Parse Gradle-specific issues from log.

        Args:
            log_content: Log content

        Returns:
            List of issue dictionaries
        """
        issues = []

        # Check for dependency resolution failures
        if "Could not resolve" in log_content or "Could not find" in log_content:
            issues.append({
                "type": "dependency_resolution",
                "severity": "error",
                "message": "Failed to resolve project dependencies"
            })

        # Check for compilation failures
        if "Compilation failed" in log_content or "Compilation error" in log_content:
            issues.append({
                "type": "compilation",
                "severity": "error",
                "message": "Kotlin/Java compilation failed"
            })

        # Check for test failures
        if "tests completed" in log_content and "failed" in log_content:
            issues.append({
                "type": "test_failure",
                "severity": "error",
                "message": "Unit or integration tests failed"
            })

        # Check for task execution failures
        task_failure = re.search(
            r"Execution failed for task '([\w:]+)'",
            log_content
        )
        if task_failure:
            issues.append({
                "type": "task_execution",
                "severity": "error",
                "message": f"Gradle task failed: {task_failure.group(1)}"
            })

        # Check for out of memory
        if "java.lang.OutOfMemoryError" in log_content:
            issues.append({
                "type": "out_of_memory",
                "severity": "error",
                "message": "Gradle build ran out of memory"
            })

        # Check for daemon issues
        if "Gradle Daemon" in log_content and ("stopped" in log_content or "died" in log_content):
            issues.append({
                "type": "daemon_crash",
                "severity": "warning",
                "message": "Gradle daemon crashed during build"
            })

        return issues

    def _generate_recommendations(self, result: AnalysisResult) -> List[str]:
        """Generate recommendations based on analysis.

        Args:
            result: Analysis result

        Returns:
            List of recommendation strings
        """
        recommendations = []

        if result.dependencies_failed:
            recommendations.append(
                "Check dependency versions and repository configuration"
            )
            recommendations.append(
                "Run './gradlew dependencies' to diagnose conflicts"
            )

        if result.compilation_errors > 0:
            recommendations.append(
                "Fix compilation errors in source code"
            )
            recommendations.append(
                "Ensure correct Java/Kotlin version is configured"
            )

        if result.test_failures > 0:
            recommendations.append(
                "Review failing test cases and fix issues"
            )
            recommendations.append(
                "Run tests locally: ./gradlew test"
            )

        for issue in result.issues:
            if issue["type"] == "out_of_memory":
                recommendations.append(
                    "Increase Gradle heap size in gradle.properties: org.gradle.jvmargs=-Xmx2048m"
                )
            elif issue["type"] == "daemon_crash":
                recommendations.append(
                    "Stop Gradle daemon and rebuild: ./gradlew --stop && ./gradlew clean build"
                )

        if not recommendations:
            recommendations.append("Review error messages for specific issues")

        return recommendations

    def _generate_summary(self, result: AnalysisResult) -> str:
        """Generate human-readable summary.

        Args:
            result: Analysis result

        Returns:
            Summary string
        """
        parts = []

        if result.compilation_errors > 0:
            parts.append(f"{result.compilation_errors} compilation error(s)")

        if result.test_failures > 0:
            parts.append(f"{result.test_failures} test failure(s)")

        if result.dependencies_failed:
            parts.append(
                f"{len(result.dependencies_failed)} dependency resolution failure(s)"
            )

        if len(result.errors) > 0:
            parts.append(f"{len(result.errors)} error message(s)")

        if parts:
            return "Gradle build failed: " + ", ".join(parts)
        else:
            return "Gradle build completed (check logs for warnings)"
