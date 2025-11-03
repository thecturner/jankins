"""NPM/Yarn build log analyzer."""

import re
from typing import List
from .base import LogAnalyzer, AnalysisResult


class NpmAnalyzer(LogAnalyzer):
    """Analyzer for NPM and Yarn builds."""

    @property
    def tool_name(self) -> str:
        return "npm"

    @property
    def detection_patterns(self) -> List[str]:
        return [
            r"npm (install|run|test|build)",
            r"yarn (install|run|test|build)",
            r"npm ERR!",
            r"node_modules",
            r"package\.json",
        ]

    def analyze(self, log_content: str) -> AnalysisResult:
        """Analyze NPM/Yarn build log.

        Args:
            log_content: NPM/Yarn build log

        Returns:
            AnalysisResult with NPM-specific information
        """
        result = AnalysisResult(
            build_tool="npm",
            detected=self.detect(log_content)
        )

        if not result.detected:
            result.summary = "NPM/Yarn build not detected in log"
            return result

        # Extract errors
        error_patterns = [
            r"npm ERR! .*",
            r"error .*",
            r"ERROR in .*",
            r"Failed to compile",
            r"Module not found: .*",
        ]
        result.errors = self.extract_errors(log_content, error_patterns)

        # Extract warnings
        warning_patterns = [
            r"npm WARN .*",
            r"warning .*",
            r"WARNING in .*",
            r"deprecated .*",
        ]
        result.warnings = self.extract_warnings(log_content, warning_patterns)

        # Parse test failures
        test_failure_patterns = [
            r"(\d+) failing",
            r"Tests:.*(\d+) failed",
            r"FAIL .*\.test\.",
        ]
        test_failures = 0
        for pattern in test_failure_patterns:
            matches = re.findall(pattern, log_content)
            if matches:
                for match in matches:
                    if isinstance(match, tuple):
                        match = match[0] if match[0] else match[1]
                    try:
                        test_failures += int(match)
                    except (ValueError, IndexError):
                        test_failures += 1
        result.test_failures = test_failures

        # Extract failed dependencies
        dep_patterns = [
            r"Could not resolve dependency:\s+([\w\@\-\/]+)",
            r"Module not found:.*['\"]([^'\"]+)['\"]",
            r"Cannot find module ['\"]([^'\"]+)['\"]",
        ]
        failed_deps = []
        for pattern in dep_patterns:
            failed_deps.extend(re.findall(pattern, log_content))
        result.dependencies_failed = list(set(failed_deps))

        # Parse specific issues
        result.issues = self._parse_npm_issues(log_content)

        # Generate recommendations
        result.recommendations = self._generate_recommendations(result)

        # Generate summary
        result.summary = self._generate_summary(result)

        return result

    def _parse_npm_issues(self, log_content: str) -> List[dict]:
        """Parse NPM-specific issues from log.

        Args:
            log_content: Log content

        Returns:
            List of issue dictionaries
        """
        issues = []

        # Check for dependency resolution failures
        if "Could not resolve dependency" in log_content or "ERESOLVE" in log_content:
            issues.append({
                "type": "dependency_resolution",
                "severity": "error",
                "message": "Failed to resolve package dependencies"
            })

        # Check for compilation/build failures
        if "Failed to compile" in log_content or "ERROR in" in log_content:
            issues.append({
                "type": "compilation",
                "severity": "error",
                "message": "Webpack/TypeScript compilation failed"
            })

        # Check for test failures
        if " failing" in log_content or "Tests:.*failed" in log_content:
            issues.append({
                "type": "test_failure",
                "severity": "error",
                "message": "Unit or integration tests failed"
            })

        # Check for missing modules
        if "Module not found" in log_content or "Cannot find module" in log_content:
            issues.append({
                "type": "missing_module",
                "severity": "error",
                "message": "Required module or package not found"
            })

        # Check for network errors
        if "ECONNREFUSED" in log_content or "ETIMEDOUT" in log_content:
            issues.append({
                "type": "network_error",
                "severity": "error",
                "message": "Network error accessing npm registry"
            })

        # Check for permission errors
        if "EACCES" in log_content or "permission denied" in log_content.lower():
            issues.append({
                "type": "permission_error",
                "severity": "error",
                "message": "Permission denied during npm operation"
            })

        # Check for out of memory
        if "JavaScript heap out of memory" in log_content:
            issues.append({
                "type": "out_of_memory",
                "severity": "error",
                "message": "Node.js ran out of heap memory"
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
                "Check package.json versions and registry availability"
            )
            recommendations.append(
                "Try clearing cache: npm cache clean --force"
            )
            recommendations.append(
                "Delete node_modules and package-lock.json, reinstall"
            )

        if result.test_failures > 0:
            recommendations.append(
                "Review failing test cases and fix issues"
            )
            recommendations.append(
                "Run tests locally: npm test"
            )

        for issue in result.issues:
            if issue["type"] == "out_of_memory":
                recommendations.append(
                    "Increase Node heap size: NODE_OPTIONS=--max-old-space-size=4096"
                )
            elif issue["type"] == "network_error":
                recommendations.append(
                    "Check npm registry connectivity and proxy settings"
                )
            elif issue["type"] == "permission_error":
                recommendations.append(
                    "Fix npm permissions or use npx/yarn"
                )
            elif issue["type"] == "missing_module":
                recommendations.append(
                    "Run npm install to install missing dependencies"
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

        if result.test_failures > 0:
            parts.append(f"{result.test_failures} test failure(s)")

        if result.dependencies_failed:
            parts.append(
                f"{len(result.dependencies_failed)} dependency issue(s)"
            )

        if len(result.errors) > 0:
            parts.append(f"{len(result.errors)} error message(s)")

        if parts:
            return "NPM/Yarn build failed: " + ", ".join(parts)
        else:
            return "NPM/Yarn build completed (check logs for warnings)"
