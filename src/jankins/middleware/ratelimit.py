"""Rate limiting middleware for MCP requests."""

import time
import logging
from typing import Dict, Tuple, Optional
from collections import defaultdict
from dataclasses import dataclass, field
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


@dataclass
class RateLimitBucket:
    """Token bucket for rate limiting."""

    capacity: int  # Maximum tokens
    refill_rate: float  # Tokens per second
    tokens: float = field(init=False)
    last_refill: float = field(init=False)

    def __post_init__(self):
        self.tokens = float(self.capacity)
        self.last_refill = time.time()

    def consume(self, tokens: int = 1) -> bool:
        """Try to consume tokens from bucket.

        Args:
            tokens: Number of tokens to consume

        Returns:
            True if tokens were consumed, False if insufficient
        """
        self._refill()

        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False

    def _refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_refill
        self.last_refill = now

        # Add tokens based on elapsed time
        self.tokens = min(
            self.capacity,
            self.tokens + (elapsed * self.refill_rate)
        )

    def time_until_available(self, tokens: int = 1) -> float:
        """Calculate seconds until enough tokens available.

        Args:
            tokens: Number of tokens needed

        Returns:
            Seconds until tokens available, 0 if already available
        """
        self._refill()

        if self.tokens >= tokens:
            return 0.0

        needed = tokens - self.tokens
        return needed / self.refill_rate


class RateLimiter:
    """Rate limiter using token bucket algorithm.

    Supports per-user and global rate limiting with configurable
    limits and cleanup of old buckets.
    """

    def __init__(
        self,
        requests_per_minute: int = 60,
        burst: int = 10,
        cleanup_interval: int = 300  # 5 minutes
    ):
        """Initialize rate limiter.

        Args:
            requests_per_minute: Sustained requests per minute
            burst: Maximum burst size
            cleanup_interval: Seconds between bucket cleanup
        """
        self.requests_per_minute = requests_per_minute
        self.burst = burst
        self.refill_rate = requests_per_minute / 60.0  # Convert to per-second

        # User/IP -> RateLimitBucket
        self.buckets: Dict[str, RateLimitBucket] = {}
        self.last_cleanup = time.time()
        self.cleanup_interval = cleanup_interval

        logger.info(
            f"Rate limiter initialized: {requests_per_minute} req/min, burst={burst}"
        )

    def check_rate_limit(self, identifier: str) -> Tuple[bool, Optional[float]]:
        """Check if request is within rate limit.

        Args:
            identifier: User ID, IP address, or other identifier

        Returns:
            Tuple of (allowed: bool, retry_after: Optional[float])
            retry_after is seconds to wait if not allowed
        """
        self._cleanup_old_buckets()

        # Get or create bucket for this identifier
        if identifier not in self.buckets:
            self.buckets[identifier] = RateLimitBucket(
                capacity=self.burst,
                refill_rate=self.refill_rate
            )

        bucket = self.buckets[identifier]

        # Try to consume a token
        if bucket.consume(1):
            return (True, None)
        else:
            retry_after = bucket.time_until_available(1)
            logger.warning(
                f"Rate limit exceeded for {identifier}",
                extra={"retry_after": retry_after}
            )
            return (False, retry_after)

    def _cleanup_old_buckets(self) -> None:
        """Remove inactive buckets to prevent memory leaks."""
        now = time.time()

        if now - self.last_cleanup < self.cleanup_interval:
            return

        # Remove buckets that are full and haven't been used recently
        inactive_threshold = now - (self.cleanup_interval * 2)
        to_remove = []

        for identifier, bucket in self.buckets.items():
            if (bucket.tokens >= bucket.capacity and
                bucket.last_refill < inactive_threshold):
                to_remove.append(identifier)

        for identifier in to_remove:
            del self.buckets[identifier]

        if to_remove:
            logger.debug(f"Cleaned up {len(to_remove)} inactive rate limit buckets")

        self.last_cleanup = now

    def get_stats(self) -> Dict[str, any]:
        """Get rate limiter statistics.

        Returns:
            Dictionary with stats
        """
        return {
            "active_buckets": len(self.buckets),
            "requests_per_minute": self.requests_per_minute,
            "burst_size": self.burst,
            "bucket_details": {
                identifier: {
                    "tokens": round(bucket.tokens, 2),
                    "capacity": bucket.capacity,
                    "last_refill": bucket.last_refill
                }
                for identifier, bucket in list(self.buckets.items())[:10]  # Top 10
            }
        }


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Starlette middleware for rate limiting MCP requests."""

    def __init__(
        self,
        app,
        rate_limiter: RateLimiter,
        enabled: bool = True
    ):
        """Initialize rate limit middleware.

        Args:
            app: ASGI application
            rate_limiter: RateLimiter instance
            enabled: Whether rate limiting is enabled
        """
        super().__init__(app)
        self.rate_limiter = rate_limiter
        self.enabled = enabled

    async def dispatch(self, request: Request, call_next):
        """Process request with rate limiting.

        Args:
            request: HTTP request
            call_next: Next middleware/handler

        Returns:
            HTTP response
        """
        if not self.enabled:
            return await call_next(request)

        # Skip rate limiting for health checks
        if request.url.path in ["/_health", "/_ready", "/_metrics"]:
            return await call_next(request)

        # Get identifier (prefer authenticated user, fallback to IP)
        identifier = self._get_identifier(request)

        # Check rate limit
        allowed, retry_after = self.rate_limiter.check_rate_limit(identifier)

        if not allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32000,  # Server error
                        "message": "Rate limit exceeded",
                        "data": {
                            "retry_after": round(retry_after, 2),
                            "limit": self.rate_limiter.requests_per_minute,
                            "identifier": identifier
                        }
                    },
                    "id": None
                },
                headers={
                    "Retry-After": str(int(retry_after) + 1),
                    "X-RateLimit-Limit": str(self.rate_limiter.requests_per_minute),
                    "X-RateLimit-Remaining": "0"
                }
            )

        # Process request
        response = await call_next(request)

        # Add rate limit headers to response
        bucket = self.rate_limiter.buckets.get(identifier)
        if bucket:
            response.headers["X-RateLimit-Limit"] = str(
                self.rate_limiter.requests_per_minute
            )
            response.headers["X-RateLimit-Remaining"] = str(int(bucket.tokens))

        return response

    def _get_identifier(self, request: Request) -> str:
        """Extract identifier from request.

        Args:
            request: HTTP request

        Returns:
            Identifier string (username or IP)
        """
        # Try to get from auth header (Basic auth username)
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Basic "):
            try:
                import base64
                decoded = base64.b64decode(auth_header[6:]).decode("utf-8")
                username = decoded.split(":")[0]
                if username:
                    return f"user:{username}"
            except Exception:
                pass

        # Fallback to client IP
        # Check X-Forwarded-For for proxied requests
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Take first IP in the chain
            client_ip = forwarded_for.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "unknown"

        return f"ip:{client_ip}"
