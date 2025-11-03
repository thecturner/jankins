"""Test token-aware formatters."""

from jankins.formatters import OutputFormat, TokenAwareFormatter, estimate_tokens


def test_estimate_tokens():
    """Test token estimation."""
    text = "This is a test sentence with multiple words."
    tokens = estimate_tokens(text)

    # Should estimate reasonable token count
    assert tokens > 0
    assert tokens < len(text)  # Tokens should be fewer than characters


def test_format_job_list_summary():
    """Test job list formatting in summary mode."""
    jobs = [
        {"fullname": "job1", "url": "http://jenkins/job/job1", "color": "blue"},
        {"fullname": "job2", "url": "http://jenkins/job/job2", "color": "red"},
    ]

    result = TokenAwareFormatter.format_job_list(jobs, format=OutputFormat.SUMMARY)

    assert result["total"] == 2
    assert result["shown"] == 2
    assert len(result["jobs"]) == 2
    assert result["jobs"][0]["name"] == "job1"
    assert result["jobs"][0]["color"] == "blue"


def test_format_job_list_ids():
    """Test job list formatting in IDs mode."""
    jobs = [
        {"fullname": "job1", "url": "http://jenkins/job/job1", "color": "blue"},
        {"fullname": "job2", "url": "http://jenkins/job/job2", "color": "red"},
    ]

    result = TokenAwareFormatter.format_job_list(jobs, format=OutputFormat.IDS)

    assert result["total"] == 2
    assert len(result["jobs"]) == 2
    assert "name" in result["jobs"][0]
    assert "url" in result["jobs"][0]
    assert "color" not in result["jobs"][0]  # Should only have name and URL


def test_format_build_summary():
    """Test build formatting in summary mode."""
    build = {
        "number": 42,
        "result": "SUCCESS",
        "duration": 135000,  # 2m 15s
        "timestamp": 1640000000000,
        "building": False,
        "url": "http://jenkins/job/test/42",
        "changeSet": {"items": [{"commit": "abc123"}]},
        "artifacts": [{"fileName": "app.jar"}]
    }

    result = TokenAwareFormatter.format_build(build, format=OutputFormat.SUMMARY)

    assert result["number"] == 42
    assert result["result"] == "SUCCESS"
    assert "duration" in result
    assert result["changes_count"] == 1
    assert result["artifacts_count"] == 1


def test_format_build_ids():
    """Test build formatting in IDs mode."""
    build = {
        "number": 42,
        "result": "FAILURE",
        "url": "http://jenkins/job/test/42",
        "duration": 135000,
    }

    result = TokenAwareFormatter.format_build(build, format=OutputFormat.IDS)

    assert result["number"] == 42
    assert result["url"] == "http://jenkins/job/test/42"
    assert result["result"] == "FAILURE"
    assert "duration" not in result  # IDs mode should be minimal


def test_add_metadata():
    """Test adding metadata to response."""
    data = {"job": "test", "result": "success"}

    result = TokenAwareFormatter.add_metadata(
        data,
        correlation_id="test-123",
        took_ms=250,
        format_used=OutputFormat.SUMMARY
    )

    assert "_meta" in result
    assert result["_meta"]["correlation_id"] == "test-123"
    assert result["_meta"]["took_ms"] == 250
    assert result["_meta"]["format"] == "summary"
    assert "token_estimate" in result["_meta"]
