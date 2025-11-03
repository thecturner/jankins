"""Maven build log analyzer."""

import re
from typing import List
from .base import LogAnalyzer, AnalysisResult


class MavenAnalyzer(LogAnalyzer):
    """Analyzer for Apache Maven builds."""

    @property
    def tool_name(self) -> str:
        return "maven"

    @property
    def detection_patterns(self) -> List[str]:
        return [
            r"Apache Maven \d+\.\d+",
            r"\[INFO\] Building .* \d+\.\d+",
            r"mvn (clean|compile|test|package|install|deploy)",
            r"\[INFO\] Scanning for projects\.\.\.",
        ]

    def analyze(self, log_content: str) -> AnalysisResult:
        """Analyze Maven build log.

        Args:
            log_content: Maven build log

        Returns:
            AnalysisResult with Maven-specific information
        """
        result = AnalysisResult(
            build_tool="maven",
            detected=self.detect(log_content)
        )

        if not result.detected:
            result.summary = "Maven build not detected in log"
            return result

        # Extract errors
        error_patterns = [
            r"\[ERROR\] .*",
            r"BUILD FAILURE",
            r"Failed to execute goal .*",
            r"Could not resolve dependencies .*",
            r"Compilation failure",
        ]
        result.errors = self.extract_errors(log_content, error_patterns)

        # Extract warnings
        warning_patterns = [
            r"\[WARNING\] .*",
        ]
        result.warnings = self.extract_warnings(log_content, warning_patterns)

        # Parse compilation errors
        compilation_pattern = r"(\d+) error[s]?"
        compilation_matches = re.findall(compilation_pattern, log_content)
        if compilation_matches:
            result.compilation_errors = sum(int(m) for m in compilation_matches)

        # Parse test failures
        test_failure_pattern = r"Tests run: \d+, Failures: (\d+), Errors: (\d+)"
        test_matches = re.findall(test_failure_pattern, log_content)
        if test_matches:
            result.test_failures = sum(
                int(failures) + int(errors)
                for failures, errors in test_matches
            )

        # Extract failed dependencies
        dep_pattern = r"Could not resolve dependencies for project ([\w\.\-:]+)"
        result.dependencies_failed = list(set(re.findall(dep_pattern, log_content)))

        # Parse specific issues
        result.issues = self._parse_maven_issues(log_content)

        # Generate recommendations
        result.recommendations = self._generate_recommendations(result)

        # Generate summary
        result.summary = self._generate_summary(result)

        return result

    def _parse_maven_issues(self, log_content: str) -> List[dict]:
        """Parse Maven-specific issues from log.

        Args:
            log_content: Log content

        Returns:
            List of issue dictionaries
        """
        issues = []

        # Check for dependency resolution failures
        if "Could not resolve dependencies" in log_content:
            issues.append({
                "type": "dependency_resolution",
                "severity": "error",
                "message": "Failed to resolve project dependencies"
            })

        # Check for compilation failures
        if "Compilation failure" in log_content or "compilation failed" in log_content.lower():
            issues.append({
                "type": "compilation",
                "severity": "error",
                "message": "Java compilation failed"
            })

        # Check for test failures
        if "There are test failures" in log_content:
            issues.append({
                "type": "test_failure",
                "severity": "error",
                "message": "Unit or integration tests failed"
            })

        # Check for plugin execution failures
        plugin_failure = re.search(
            r"Failed to execute goal ([\w\.\-:]+)",
            log_content
        )
        if plugin_failure:
            issues.append({
                "type": "plugin_execution",
                "severity": "error",
                "message": f"Maven plugin failed: {plugin_failure.group(1)}"
            })

        # Check for out of memory
        if "java.lang.OutOfMemoryError" in log_content:
            issues.append({
                "type": "out_of_memory",
                "severity": "error",
                "message": "Maven build ran out of memory"
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
                "Check dependency versions and repository availability"
            )
            recommendations.append(
                "Run 'mvn dependency:tree' to diagnose dependency conflicts"
            )

        if result.compilation_errors > 0:
            recommendations.append(
                "Fix compilation errors in source code"
            )
            recommendations.append(
                "Ensure correct Java version is configured"
            )

        if result.test_failures > 0:
            recommendations.append(
                "Review failing test cases and fix issues"
            )
            recommendations.append(
                "Run tests locally: mvn test"
            )

        for issue in result.issues:
            if issue["type"] == "out_of_memory":
                recommendations.append(
                    "Increase Maven heap size: MAVEN_OPTS='-Xmx2048m'"
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
            return "Maven build failed: " + ", ".join(parts)
        else:
            return "Maven build completed (check logs for warnings)"
