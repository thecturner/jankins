"""Pluggable log analyzers for different build tools."""

from .base import LogAnalyzer, AnalysisResult
from .maven import MavenAnalyzer
from .gradle import GradleAnalyzer
from .npm import NpmAnalyzer


__all__ = [
    "LogAnalyzer",
    "AnalysisResult",
    "MavenAnalyzer",
    "GradleAnalyzer",
    "NpmAnalyzer",
    "get_analyzer",
]


def get_analyzer(build_tool: str) -> LogAnalyzer:
    """Get analyzer for a specific build tool.

    Args:
        build_tool: Build tool name (maven, gradle, npm, etc.)

    Returns:
        LogAnalyzer instance

    Raises:
        ValueError: If build tool not supported
    """
    analyzers = {
        "maven": MavenAnalyzer(),
        "gradle": GradleAnalyzer(),
        "npm": NpmAnalyzer(),
        "yarn": NpmAnalyzer(),  # NPM analyzer works for yarn too
    }

    analyzer = analyzers.get(build_tool.lower())
    if not analyzer:
        raise ValueError(
            f"Unsupported build tool: {build_tool}. "
            f"Supported: {', '.join(analyzers.keys())}"
        )

    return analyzer
