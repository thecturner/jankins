"""Tests for response caching."""

import pytest
import time
from jankins.cache import ResponseCache


@pytest.mark.unit
class TestResponseCache:
    """Test response cache functionality."""

    def test_cache_init(self, response_cache):
        """Test cache initialization."""
        assert response_cache.ttl_seconds == 60
        assert response_cache.max_size == 100
        assert response_cache.stats["hits"] == 0
        assert response_cache.stats["misses"] == 0

    def test_cache_set_and_get(self, response_cache):
        """Test setting and getting cached values."""
        response_cache.set("key1", {"data": "value1"})
        result = response_cache.get("key1")
        assert result == {"data": "value1"}
        assert response_cache.stats["hits"] == 1

    def test_cache_miss(self, response_cache):
        """Test cache miss."""
        result = response_cache.get("nonexistent")
        assert result is None
        assert response_cache.stats["misses"] == 1

    def test_cache_expiration(self):
        """Test cache TTL expiration."""
        cache = ResponseCache(ttl_seconds=1, max_size=10)
        cache.set("key1", "value1")

        # Should be cached
        assert cache.get("key1") == "value1"

        # Wait for expiration
        time.sleep(1.1)

        # Should be expired
        assert cache.get("key1") is None

    def test_cache_max_size(self):
        """Test cache size limit."""
        cache = ResponseCache(ttl_seconds=60, max_size=3)

        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")

        # All should be cached
        assert cache.get("key1") == "value1"
        assert cache.get("key2") == "value2"
        assert cache.get("key3") == "value3"

        # Add one more - should evict oldest
        cache.set("key4", "value4")

        # key1 should be evicted
        assert cache.get("key1") is None
        assert cache.get("key4") == "value4"

    def test_cache_clear(self, response_cache):
        """Test cache clearing."""
        response_cache.set("key1", "value1")
        response_cache.set("key2", "value2")

        response_cache.clear()

        assert response_cache.get("key1") is None
        assert response_cache.get("key2") is None
        assert len(response_cache._cache) == 0

    def test_cache_stats(self, response_cache):
        """Test cache statistics."""
        response_cache.set("key1", "value1")
        response_cache.get("key1")  # hit
        response_cache.get("key1")  # hit
        response_cache.get("key2")  # miss

        stats = response_cache.get_stats()
        assert stats["hits"] == 2
        assert stats["misses"] == 1
        assert stats["size"] == 1
        assert stats["hit_rate"] == 2.0 / 3.0

    def test_cache_invalidate(self, response_cache):
        """Test cache invalidation."""
        response_cache.set("key1", "value1")
        assert response_cache.get("key1") == "value1"

        response_cache.invalidate("key1")
        assert response_cache.get("key1") is None
