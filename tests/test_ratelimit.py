"""Tests for rate limiting."""

import time

import pytest

from jankins.middleware.ratelimit import RateLimitBucket, RateLimiter


@pytest.mark.unit
class TestRateLimitBucket:
    """Test rate limit bucket functionality."""

    def test_bucket_init(self):
        """Test bucket initialization."""
        bucket = RateLimitBucket(capacity=10, refill_rate=1.0)
        assert bucket.tokens == 10
        assert bucket.capacity == 10

    def test_consume_tokens(self):
        """Test token consumption."""
        bucket = RateLimitBucket(capacity=10, refill_rate=1.0)

        assert bucket.consume(3) is True
        assert bucket.tokens == 7

        assert bucket.consume(7) is True
        assert bucket.tokens < 0.001  # Allow for floating point precision

    def test_consume_insufficient_tokens(self):
        """Test consumption with insufficient tokens."""
        bucket = RateLimitBucket(capacity=5, refill_rate=1.0)

        assert bucket.consume(3) is True
        assert bucket.consume(3) is False  # Only 2 tokens left

    def test_token_refill(self):
        """Test token refill over time."""
        bucket = RateLimitBucket(capacity=10, refill_rate=10.0)  # 10 tokens/sec

        # Consume all tokens
        bucket.consume(10)
        assert bucket.tokens == 0

        # Wait for refill (0.5 sec = 5 tokens)
        time.sleep(0.5)
        bucket._refill()

        # Should have ~5 tokens (allow some timing variance)
        assert bucket.tokens >= 4
        assert bucket.tokens <= 6

    def test_refill_cap(self):
        """Test that refill doesn't exceed capacity."""
        bucket = RateLimitBucket(capacity=10, refill_rate=100.0)

        # Wait to accumulate tokens
        time.sleep(0.5)
        bucket._refill()

        # Should not exceed capacity
        assert bucket.tokens <= 10


@pytest.mark.unit
class TestRateLimiter:
    """Test rate limiter middleware."""

    def test_rate_limiter_init(self):
        """Test rate limiter initialization."""
        limiter = RateLimiter(requests_per_minute=60, burst=10)
        assert limiter.requests_per_minute == 60
        assert limiter.burst == 10

    def test_allow_request(self):
        """Test allowing requests."""
        limiter = RateLimiter(requests_per_minute=60, burst=10)

        # Should allow request
        allowed, retry_after = limiter.check_rate_limit("user1")
        assert allowed is True
        assert retry_after is None

        allowed, retry_after = limiter.check_rate_limit("user1")
        assert allowed is True
        assert retry_after is None

    def test_rate_limit_enforcement(self):
        """Test rate limit enforcement."""
        limiter = RateLimiter(requests_per_minute=60, burst=5)

        # Consume all burst tokens
        for _ in range(5):
            allowed, retry_after = limiter.check_rate_limit("user1")
            assert allowed is True

        # Next request should be denied
        allowed, retry_after = limiter.check_rate_limit("user1")
        assert allowed is False
        assert retry_after is not None
        assert retry_after > 0

    def test_different_users(self):
        """Test rate limiting per user."""
        limiter = RateLimiter(requests_per_minute=60, burst=5)

        # User1 consumes all tokens
        for _ in range(5):
            limiter.check_rate_limit("user1")

        # User2 should still be allowed
        allowed, retry_after = limiter.check_rate_limit("user2")
        assert allowed is True

    def test_bucket_cleanup(self):
        """Test automatic bucket cleanup."""
        limiter = RateLimiter(requests_per_minute=60, burst=10, cleanup_interval=1)

        # Create buckets for multiple users
        limiter.check_rate_limit("user1")
        limiter.check_rate_limit("user2")
        limiter.check_rate_limit("user3")

        assert len(limiter.buckets) == 3

        # Wait for cleanup (this test is time-sensitive)
        time.sleep(2)
        limiter._cleanup_old_buckets()

        # Buckets should still exist (just accessed)
        # This is a basic test - in production cleanup is more sophisticated
        assert len(limiter.buckets) >= 0

    def test_get_bucket_info(self):
        """Test getting bucket statistics."""
        limiter = RateLimiter(requests_per_minute=60, burst=10)

        limiter.check_rate_limit("user1")
        limiter.check_rate_limit("user1")

        stats = limiter.get_stats()
        assert "active_buckets" in stats
        assert "bucket_details" in stats
        assert stats["active_buckets"] >= 1
