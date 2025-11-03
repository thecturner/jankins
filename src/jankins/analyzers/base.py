"""Base classes for log analyzers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import re


@dataclass
class AnalysisResult:
    """Result of log analysis."""

    build_tool: str
    detected: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    issues: List[Dict[str, Any]] = field(default_factory=list)

    # Build tool specific metrics
    dependencies_failed: List[str] = field(default_factory=list)
    compilation_errors: int = 0
    test_failures: int = 0

    # Recommendations
    recommendations: List[str] = field(default_factory=list)

    # Summary
    summary: str = ""


class LogAnalyzer(ABC):
    """Base class for build tool log analyzers."""

    @property
    @abstractmethod
    def tool_name(self) -> str:
        """Name of the build tool."""
        pass

    @property
    @abstractmethod
    def detection_patterns(self) -> List[str]:
        """Regex patterns to detect if this tool was used."""
        pass

    @abstractmethod
    def analyze(self, log_content: str) -> AnalysisResult:
        """Analyze build log content.

        Args:
            log_content: Full or partial build log

        Returns:
            AnalysisResult with parsed information
        """
        pass

    def detect(self, log_content: str) -> bool:
        """Check if this build tool was used in the build.

        Args:
            log_content: Build log content

        Returns:
            True if tool detected, False otherwise
        """
        for pattern in self.detection_patterns:
            if re.search(pattern, log_content, re.IGNORECASE | re.MULTILINE):
                return True
        return False

    def extract_errors(self, log_content: str, patterns: List[str]) -> List[str]:
        """Extract error messages using patterns.

        Args:
            log_content: Log content
            patterns: List of regex patterns

        Returns:
            List of extracted error messages
        """
        errors = []
        for pattern in patterns:
            matches = re.finditer(pattern, log_content, re.MULTILINE | re.IGNORECASE)
            for match in matches:
                error = match.group(0).strip()
                if error and len(error) < 500:  # Reasonable length
                    errors.append(error)

        # Deduplicate while preserving order
        seen = set()
        unique_errors = []
        for error in errors:
            if error not in seen:
                seen.add(error)
                unique_errors.append(error)

        return unique_errors[:20]  # Top 20

    def extract_warnings(self, log_content: str, patterns: List[str]) -> List[str]:
        """Extract warning messages using patterns.

        Args:
            log_content: Log content
            patterns: List of regex patterns

        Returns:
            List of extracted warning messages
        """
        return self.extract_errors(log_content, patterns)  # Same logic
