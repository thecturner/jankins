"""Tests for metrics collection."""

import pytest


@pytest.mark.unit
class TestMetricsCollector:
    """Test metrics collector functionality."""

    def test_metrics_init(self, metrics_collector):
        """Test metrics initialization."""
        assert metrics_collector.summary.total_requests == 0
        assert len(metrics_collector._durations) == 0

    def test_record_request_success(self, metrics_collector):
        """Test recording successful request."""
        metrics_collector.record_request("get_build", 100.0, success=True)

        assert metrics_collector.summary.total_requests == 1
        assert metrics_collector.summary.successful_requests == 1
        assert metrics_collector.summary.failed_requests == 0
        assert metrics_collector.summary.tool_calls["get_build"] == 1

    def test_record_request_failure(self, metrics_collector):
        """Test recording failed request."""
        metrics_collector.record_request("get_build", 150.0, success=False, error_type="NotFound")

        assert metrics_collector.summary.total_requests == 1
        assert metrics_collector.summary.successful_requests == 0
        assert metrics_collector.summary.failed_requests == 1
        assert metrics_collector.summary.tool_errors["get_build:NotFound"] == 1

    def test_record_jenkins_call(self, metrics_collector):
        """Test recording Jenkins API call."""
        metrics_collector.record_jenkins_call(success=True)

        assert metrics_collector.summary.jenkins_calls == 1
        assert metrics_collector.summary.jenkins_errors == 0

    def test_duration_percentiles(self, metrics_collector):
        """Test duration percentile calculations."""
        # Record multiple requests with known durations
        for duration in [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]:
            metrics_collector.record_request("test", duration, success=True)

        summary = metrics_collector.get_summary()

        assert "duration_ms" in summary
        assert "p50" in summary["duration_ms"]
        assert "p95" in summary["duration_ms"]
        assert "p99" in summary["duration_ms"]
        assert summary["duration_ms"]["p50"] >= 40
        assert summary["duration_ms"]["p95"] >= 90

    def test_export_prometheus(self, metrics_collector):
        """Test Prometheus format export."""
        metrics_collector.record_request("get_build", 100.0, success=True)
        metrics_collector.record_request("list_jobs", 50.0, success=True)
        metrics_collector.record_jenkins_call(success=True)

        prometheus_text = metrics_collector.export_prometheus()

        assert "jankins_requests_total" in prometheus_text
        assert "jankins_request_duration_ms" in prometheus_text
        assert "jankins_jenkins_calls_total" in prometheus_text
        assert "get_build" in prometheus_text
        assert "list_jobs" in prometheus_text

    def test_multiple_tool_usage(self, metrics_collector):
        """Test tracking multiple tool usages."""
        metrics_collector.record_request("get_build", 100.0, success=True)
        metrics_collector.record_request("get_build", 120.0, success=True)
        metrics_collector.record_request("list_jobs", 50.0, success=True)

        assert metrics_collector.summary.tool_calls["get_build"] == 2
        assert metrics_collector.summary.tool_calls["list_jobs"] == 1

    def test_error_tracking(self, metrics_collector):
        """Test error type tracking."""
        metrics_collector.record_request("get_build", 100.0, False, "NotFound")
        metrics_collector.record_request("get_build", 100.0, False, "NotFound")
        metrics_collector.record_request("list_jobs", 100.0, False, "Timeout")

        summary = metrics_collector.get_summary()
        # Errors are tracked as "tool:error_type"
        assert summary["tools"]["top_errors"]["get_build:NotFound"] == 2
        assert summary["tools"]["top_errors"]["list_jobs:Timeout"] == 1
