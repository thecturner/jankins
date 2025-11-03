"""Prometheus metrics for jankins MCP server.

Tracks request counts, durations, errors, and Jenkins API calls.
"""

import time
import logging
from typing import Dict, List
from collections import defaultdict, Counter
from dataclasses import dataclass, field
from threading import Lock


logger = logging.getLogger(__name__)


@dataclass
class MetricsSummary:
    """Summary of server metrics."""

    # Request metrics
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0

    # Tool call metrics
    tool_calls: Counter = field(default_factory=Counter)
    tool_errors: Counter = field(default_factory=Counter)

    # Timing metrics (in milliseconds)
    total_duration_ms: float = 0.0
    avg_duration_ms: float = 0.0
    min_duration_ms: float = float('inf')
    max_duration_ms: float = 0.0

    # Jenkins API metrics
    jenkins_calls: int = 0
    jenkins_errors: int = 0

    # Rate limit metrics
    rate_limit_hits: int = 0

    # Uptime
    start_time: float = field(default_factory=time.time)

    @property
    def uptime_seconds(self) -> float:
        """Calculate uptime in seconds."""
        return time.time() - self.start_time

    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.total_requests == 0:
            return 100.0
        return (self.successful_requests / self.total_requests) * 100


class MetricsCollector:
    """Collector for Prometheus-style metrics.

    Tracks various metrics about MCP server operations:
    - Request counts and durations
    - Tool usage statistics
    - Error rates
    - Jenkins API calls
    """

    def __init__(self):
        """Initialize metrics collector."""
        self.summary = MetricsSummary()
        self._durations: List[float] = []
        self._lock = Lock()

        logger.info("Metrics collector initialized")

    def record_request(
        self,
        tool_name: str,
        duration_ms: float,
        success: bool,
        error_type: str = None
    ) -> None:
        """Record a tool request.

        Args:
            tool_name: Name of the tool called
            duration_ms: Request duration in milliseconds
            success: Whether request was successful
            error_type: Type of error if failed
        """
        with self._lock:
            self.summary.total_requests += 1

            if success:
                self.summary.successful_requests += 1
            else:
                self.summary.failed_requests += 1
                if error_type:
                    self.summary.tool_errors[f"{tool_name}:{error_type}"] += 1

            # Track tool usage
            self.summary.tool_calls[tool_name] += 1

            # Track duration
            self.summary.total_duration_ms += duration_ms
            self.summary.min_duration_ms = min(
                self.summary.min_duration_ms, duration_ms
            )
            self.summary.max_duration_ms = max(
                self.summary.max_duration_ms, duration_ms
            )

            # Keep last 1000 durations for percentile calculation
            self._durations.append(duration_ms)
            if len(self._durations) > 1000:
                self._durations.pop(0)

            # Update average
            if self.summary.total_requests > 0:
                self.summary.avg_duration_ms = (
                    self.summary.total_duration_ms / self.summary.total_requests
                )

    def record_jenkins_call(self, success: bool = True) -> None:
        """Record a Jenkins API call.

        Args:
            success: Whether the call was successful
        """
        with self._lock:
            self.summary.jenkins_calls += 1
            if not success:
                self.summary.jenkins_errors += 1

    def record_rate_limit_hit(self) -> None:
        """Record a rate limit violation."""
        with self._lock:
            self.summary.rate_limit_hits += 1

    def get_percentile(self, percentile: float) -> float:
        """Calculate duration percentile.

        Args:
            percentile: Percentile to calculate (0-100)

        Returns:
            Duration at percentile in milliseconds
        """
        with self._lock:
            if not self._durations:
                return 0.0

            sorted_durations = sorted(self._durations)
            index = int(len(sorted_durations) * (percentile / 100))
            index = min(index, len(sorted_durations) - 1)
            return sorted_durations[index]

    def get_summary(self) -> Dict:
        """Get metrics summary.

        Returns:
            Dictionary with metrics summary
        """
        with self._lock:
            p50 = self.get_percentile(50)
            p95 = self.get_percentile(95)
            p99 = self.get_percentile(99)

            return {
                "uptime_seconds": round(self.summary.uptime_seconds, 2),
                "requests": {
                    "total": self.summary.total_requests,
                    "successful": self.summary.successful_requests,
                    "failed": self.summary.failed_requests,
                    "success_rate": round(self.summary.success_rate, 2)
                },
                "duration_ms": {
                    "avg": round(self.summary.avg_duration_ms, 2),
                    "min": round(self.summary.min_duration_ms, 2) if self.summary.min_duration_ms != float('inf') else 0,
                    "max": round(self.summary.max_duration_ms, 2),
                    "p50": round(p50, 2),
                    "p95": round(p95, 2),
                    "p99": round(p99, 2)
                },
                "tools": {
                    "top_calls": dict(self.summary.tool_calls.most_common(10)),
                    "top_errors": dict(self.summary.tool_errors.most_common(10))
                },
                "jenkins": {
                    "calls": self.summary.jenkins_calls,
                    "errors": self.summary.jenkins_errors,
                    "error_rate": round(
                        (self.summary.jenkins_errors / self.summary.jenkins_calls * 100)
                        if self.summary.jenkins_calls > 0 else 0, 2
                    )
                },
                "rate_limiting": {
                    "hits": self.summary.rate_limit_hits
                }
            }

    def export_prometheus(self) -> str:
        """Export metrics in Prometheus text format.

        Returns:
            Prometheus-formatted metrics string
        """
        with self._lock:
            lines = []

            # Uptime
            lines.append("# HELP jankins_uptime_seconds Server uptime in seconds")
            lines.append("# TYPE jankins_uptime_seconds gauge")
            lines.append(f"jankins_uptime_seconds {self.summary.uptime_seconds:.2f}")

            # Total requests
            lines.append("# HELP jankins_requests_total Total number of requests")
            lines.append("# TYPE jankins_requests_total counter")
            lines.append(f"jankins_requests_total {self.summary.total_requests}")

            # Successful requests
            lines.append("# HELP jankins_requests_success_total Successful requests")
            lines.append("# TYPE jankins_requests_success_total counter")
            lines.append(f"jankins_requests_success_total {self.summary.successful_requests}")

            # Failed requests
            lines.append("# HELP jankins_requests_failed_total Failed requests")
            lines.append("# TYPE jankins_requests_failed_total counter")
            lines.append(f"jankins_requests_failed_total {self.summary.failed_requests}")

            # Request duration
            lines.append("# HELP jankins_request_duration_ms Request duration in milliseconds")
            lines.append("# TYPE jankins_request_duration_ms summary")
            lines.append(f"jankins_request_duration_ms_sum {self.summary.total_duration_ms:.2f}")
            lines.append(f"jankins_request_duration_ms_count {self.summary.total_requests}")
            lines.append(f"jankins_request_duration_ms{{quantile=\"0.5\"}} {self.get_percentile(50):.2f}")
            lines.append(f"jankins_request_duration_ms{{quantile=\"0.95\"}} {self.get_percentile(95):.2f}")
            lines.append(f"jankins_request_duration_ms{{quantile=\"0.99\"}} {self.get_percentile(99):.2f}")

            # Tool calls by name
            lines.append("# HELP jankins_tool_calls_total Tool calls by name")
            lines.append("# TYPE jankins_tool_calls_total counter")
            for tool_name, count in self.summary.tool_calls.items():
                lines.append(f"jankins_tool_calls_total{{tool=\"{tool_name}\"}} {count}")

            # Tool errors
            lines.append("# HELP jankins_tool_errors_total Tool errors by name and type")
            lines.append("# TYPE jankins_tool_errors_total counter")
            for error_key, count in self.summary.tool_errors.items():
                tool, error_type = error_key.split(":", 1) if ":" in error_key else (error_key, "unknown")
                lines.append(
                    f"jankins_tool_errors_total{{tool=\"{tool}\",error_type=\"{error_type}\"}} {count}"
                )

            # Jenkins API calls
            lines.append("# HELP jankins_jenkins_calls_total Jenkins API calls")
            lines.append("# TYPE jankins_jenkins_calls_total counter")
            lines.append(f"jankins_jenkins_calls_total {self.summary.jenkins_calls}")

            lines.append("# HELP jankins_jenkins_errors_total Jenkins API errors")
            lines.append("# TYPE jankins_jenkins_errors_total counter")
            lines.append(f"jankins_jenkins_errors_total {self.summary.jenkins_errors}")

            # Rate limit hits
            lines.append("# HELP jankins_rate_limit_hits_total Rate limit violations")
            lines.append("# TYPE jankins_rate_limit_hits_total counter")
            lines.append(f"jankins_rate_limit_hits_total {self.summary.rate_limit_hits}")

            return "\n".join(lines) + "\n"


# Global metrics collector instance
_metrics_collector: MetricsCollector = None


def get_metrics_collector() -> MetricsCollector:
    """Get global metrics collector instance.

    Returns:
        MetricsCollector instance
    """
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector
