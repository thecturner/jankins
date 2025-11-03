"""Simple in-memory caching layer for Jenkins API responses.

Caches responses to reduce load on Jenkins and improve performance for
frequently requested resources like job info and build data.
"""

import time
import logging
import hashlib
import json
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass
from threading import Lock

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Cache entry with expiration."""
    value: Any
    expires_at: float


class ResponseCache:
    """Simple TTL-based in-memory cache for API responses.

    Thread-safe cache with automatic expiration and size limits.
    """

    def __init__(self, ttl: int = 300, max_entries: int = 1000):
        """Initialize response cache.

        Args:
            ttl: Time-to-live in seconds
            max_entries: Maximum number of cache entries
        """
        self.ttl = ttl
        self.max_entries = max_entries
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = Lock()
        self._hits = 0
        self._misses = 0

        logger.info(f"Response cache initialized: TTL={ttl}s, max_entries={max_entries}")

    def get(self, key: str) -> Optional[Any]:
        """Get cached value if available and not expired.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        with self._lock:
            entry = self._cache.get(key)

            if entry is None:
                self._misses += 1
                return None

            # Check expiration
            if time.time() > entry.expires_at:
                del self._cache[key]
                self._misses += 1
                return None

            self._hits += 1
            return entry.value

    def set(self, key: str, value: Any) -> None:
        """Set cache value with TTL.

        Args:
            key: Cache key
            value: Value to cache
        """
        with self._lock:
            # Enforce size limit
            if len(self._cache) >= self.max_entries:
                self._evict_oldest()

            self._cache[key] = CacheEntry(
                value=value,
                expires_at=time.time() + self.ttl
            )

    def delete(self, key: str) -> None:
        """Delete cached value.

        Args:
            key: Cache key
        """
        with self._lock:
            self._cache.pop(key, None)

    def clear(self) -> None:
        """Clear all cached values."""
        with self._lock:
            self._cache.clear()
            logger.info("Cache cleared")

    def _evict_oldest(self) -> None:
        """Evict oldest cache entry."""
        if not self._cache:
            return

        # Find entry with earliest expiration
        oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k].expires_at)
        del self._cache[oldest_key]

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with cache stats
        """
        with self._lock:
            total_requests = self._hits + self._misses
            hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0

            return {
                "entries": len(self._cache),
                "max_entries": self.max_entries,
                "ttl_seconds": self.ttl,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": round(hit_rate, 2),
                "total_requests": total_requests
            }


def cache_key_from_args(
    tool_name: str,
    args: Dict[str, Any],
    exclude_keys: list = None
) -> str:
    """Generate cache key from tool name and arguments.

    Args:
        tool_name: Name of the tool
        args: Tool arguments
        exclude_keys: Keys to exclude from cache key (e.g., format)

    Returns:
        Cache key string
    """
    exclude_keys = exclude_keys or ["format"]

    # Filter out excluded keys
    filtered_args = {
        k: v for k, v in args.items()
        if k not in exclude_keys
    }

    # Create stable key from tool name and args
    key_data = {
        "tool": tool_name,
        "args": filtered_args
    }

    # Hash for consistent key
    key_json = json.dumps(key_data, sort_keys=True)
    key_hash = hashlib.sha256(key_json.encode()).hexdigest()[:16]

    return f"{tool_name}:{key_hash}"


def cached_tool(
    cache: ResponseCache,
    cacheable_tools: list = None
):
    """Decorator to add caching to tool handlers.

    Args:
        cache: ResponseCache instance
        cacheable_tools: List of tool names to cache (None = all)

    Returns:
        Decorator function
    """
    cacheable_tools = cacheable_tools or [
        "get_job",
        "get_build",
        "get_job_scm",
        "get_build_scm",
        "get_status",
        "whoami",
    ]

    def decorator(handler: Callable):
        async def wrapper(args: Dict[str, Any]) -> Dict[str, Any]:
            # Extract tool name (assuming it's in the function name or context)
            tool_name = handler.__name__.replace("_handler", "")

            # Only cache if tool is in cacheable list
            if tool_name not in cacheable_tools:
                return await handler(args)

            # Generate cache key
            cache_key = cache_key_from_args(tool_name, args)

            # Try to get from cache
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                logger.debug(f"Cache hit for {tool_name}")
                return cached_value

            # Cache miss - call handler
            logger.debug(f"Cache miss for {tool_name}")
            result = await handler(args)

            # Cache successful responses (no errors)
            if "error" not in result:
                cache.set(cache_key, result)

            return result

        return wrapper

    return decorator


# Global cache instance
_response_cache: Optional[ResponseCache] = None


def get_response_cache(ttl: int = 300, max_entries: int = 1000) -> ResponseCache:
    """Get global response cache instance.

    Args:
        ttl: Time-to-live in seconds (used on first initialization)
        max_entries: Maximum entries (used on first initialization)

    Returns:
        ResponseCache instance
    """
    global _response_cache
    if _response_cache is None:
        _response_cache = ResponseCache(ttl=ttl, max_entries=max_entries)
    return _response_cache
