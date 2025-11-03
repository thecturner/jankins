"""Tests for metrics collection."""

import pytest
from jankins.metrics import MetricsCollector


@pytest.mark.unit
class TestMetricsCollector:
    """Test metrics collector functionality."""

    def test_metrics_init(self, metrics_collector):
        """Test metrics initialization."""
        assert metrics_collector.requests_total == 0
        assert len(metrics_collector.durations) == 0

    def test_record_request_success(self, metrics_collector):
        """Test recording successful request."""
        metrics_collector.record_request("get_build", 100.0, success=True)

        assert metrics_collector.requests_total == 1
        assert metrics_collector.requests_success == 1
        assert metrics_collector.requests_failed == 0
        assert "get_build" in metrics_collector.tool_usage

    def test_record_request_failure(self, metrics_collector):
        """Test recording failed request."""
        metrics_collector.record_request(
            "get_build", 150.0, success=False, error_type="NotFound"
        )

        assert metrics_collector.requests_total == 1
        assert metrics_collector.requests_success == 0
        assert metrics_collector.requests_failed == 1
        assert "NotFound" in metrics_collector.error_counts

    def test_record_jenkins_call(self, metrics_collector):
        """Test recording Jenkins API call."""
        metrics_collector.record_jenkins_call("get_job_info", 50.0, success=True)

        assert metrics_collector.jenkins_calls_total == 1
        assert len(metrics_collector.jenkins_durations) == 1

    def test_duration_percentiles(self, metrics_collector):
        """Test duration percentile calculations."""
        # Record multiple requests with known durations
        for duration in [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]:
            metrics_collector.record_request("test", duration, success=True)

        stats = metrics_collector.get_stats()

        assert "p50" in stats
        assert "p95" in stats
        assert "p99" in stats
        assert stats["p50"] >= 40
        assert stats["p95"] >= 90

    def test_export_prometheus(self, metrics_collector):
        """Test Prometheus format export."""
        metrics_collector.record_request("get_build", 100.0, success=True)
        metrics_collector.record_request("list_jobs", 50.0, success=True)
        metrics_collector.record_jenkins_call("get_job_info", 25.0, success=True)

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

        stats = metrics_collector.get_stats()
        assert stats["tool_usage"]["get_build"] == 2
        assert stats["tool_usage"]["list_jobs"] == 1

    def test_error_tracking(self, metrics_collector):
        """Test error type tracking."""
        metrics_collector.record_request("get_build", 100.0, False, "NotFound")
        metrics_collector.record_request("get_build", 100.0, False, "NotFound")
        metrics_collector.record_request("list_jobs", 100.0, False, "Timeout")

        stats = metrics_collector.get_stats()
        assert stats["error_counts"]["NotFound"] == 2
        assert stats["error_counts"]["Timeout"] == 1
