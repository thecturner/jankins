"""Error taxonomy and exception framework for jankins.

Maps failures to MCP/JSON-RPC error codes with remediation hints.
Follows best practices for error handling in MCP servers.
"""

from typing import Optional, List
import uuid
from enum import Enum


class ErrorCode(Enum):
    """MCP-compliant error codes mapped to JSON-RPC semantics."""

    # JSON-RPC standard codes
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603

    # Application-specific codes (range: -32000 to -32099)
    UNAUTHORIZED = -32001
    FORBIDDEN = -32002
    NOT_FOUND = -32003
    CONFLICT = -32004
    RATE_LIMITED = -32005
    UPSTREAM_ERROR = -32006
    TIMEOUT = -32007


class JankinsError(Exception):
    """Base exception for all jankins errors.

    Includes correlation ID, error code, message, hints, and docs URL.
    """

    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.INTERNAL_ERROR,
        hint: Optional[str] = None,
        next_actions: Optional[List[str]] = None,
        correlation_id: Optional[str] = None,
        docs_url: Optional[str] = None,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.hint = hint or self._default_hint()
        self.next_actions = next_actions or []
        self.correlation_id = correlation_id or str(uuid.uuid4())
        self.docs_url = docs_url or "https://github.com/your-org/jankins#troubleshooting"

    def _default_hint(self) -> str:
        """Provide default hint based on error code."""
        hints = {
            ErrorCode.UNAUTHORIZED: "Check that JENKINS_USER and JENKINS_API_TOKEN are correct",
            ErrorCode.FORBIDDEN: "User lacks permissions for this operation",
            ErrorCode.NOT_FOUND: "Resource does not exist or path is incorrect",
            ErrorCode.CONFLICT: "Resource is locked or operation conflicts with current state",
            ErrorCode.RATE_LIMITED: "Too many requests, wait before retrying",
            ErrorCode.UPSTREAM_ERROR: "Jenkins server returned an error",
            ErrorCode.TIMEOUT: "Request to Jenkins timed out",
            ErrorCode.INVALID_PARAMS: "One or more parameters are invalid",
        }
        return hints.get(self.code, "An unexpected error occurred")

    def to_dict(self) -> dict:
        """Convert error to MCP-compatible error response."""
        return {
            "code": self.code.value,
            "message": self.message,
            "data": {
                "correlation_id": self.correlation_id,
                "hint": self.hint,
                "next_actions": self.next_actions,
                "docs_url": self.docs_url,
            }
        }


class InvalidParamsError(JankinsError):
    """Invalid parameters provided to a tool."""

    def __init__(self, message: str, **kwargs):
        super().__init__(message, code=ErrorCode.INVALID_PARAMS, **kwargs)


class UnauthorizedError(JankinsError):
    """Authentication failed."""

    def __init__(self, message: str = "Authentication failed", **kwargs):
        kwargs.setdefault("next_actions", [
            "Verify JENKINS_USER is correct",
            "Regenerate JENKINS_API_TOKEN from Jenkins user settings",
            "Check Jenkins server is accessible"
        ])
        super().__init__(message, code=ErrorCode.UNAUTHORIZED, **kwargs)


class ForbiddenError(JankinsError):
    """User lacks permissions."""

    def __init__(self, message: str, **kwargs):
        kwargs.setdefault("next_actions", [
            "Check user has required Jenkins permissions",
            "Contact Jenkins administrator for access",
        ])
        super().__init__(message, code=ErrorCode.FORBIDDEN, **kwargs)


class NotFoundError(JankinsError):
    """Resource not found."""

    def __init__(self, message: str, resource_type: str = "Resource", **kwargs):
        kwargs.setdefault("hint", f"{resource_type} not found or path is incorrect")
        super().__init__(message, code=ErrorCode.NOT_FOUND, **kwargs)


class ConflictError(JankinsError):
    """Operation conflicts with current state."""

    def __init__(self, message: str, **kwargs):
        super().__init__(message, code=ErrorCode.CONFLICT, **kwargs)


class RateLimitedError(JankinsError):
    """Rate limit exceeded."""

    def __init__(self, message: str, retry_after_ms: int = 60000, **kwargs):
        self.retry_after_ms = retry_after_ms
        kwargs.setdefault("hint", f"Wait {retry_after_ms}ms before retrying")
        super().__init__(message, code=ErrorCode.RATE_LIMITED, **kwargs)

    def to_dict(self) -> dict:
        """Include retry_after_ms in error data."""
        result = super().to_dict()
        result["data"]["retry_after_ms"] = self.retry_after_ms
        return result


class UpstreamError(JankinsError):
    """Jenkins server returned an error."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        **kwargs
    ):
        self.status_code = status_code
        if status_code:
            message = f"Jenkins returned {status_code}: {message}"
        super().__init__(message, code=ErrorCode.UPSTREAM_ERROR, **kwargs)


class TimeoutError(JankinsError):
    """Request timed out."""

    def __init__(self, message: str = "Request to Jenkins timed out", **kwargs):
        kwargs.setdefault("next_actions", [
            "Check Jenkins server is responsive",
            "Increase JENKINS_TIMEOUT setting",
            "Check network connectivity"
        ])
        super().__init__(message, code=ErrorCode.TIMEOUT, **kwargs)


def map_http_error(status_code: int, message: str) -> JankinsError:
    """Map HTTP status code to appropriate JankinsError."""
    if status_code == 401:
        return UnauthorizedError(message)
    elif status_code == 403:
        return ForbiddenError(message)
    elif status_code == 404:
        return NotFoundError(message)
    elif status_code == 409:
        return ConflictError(message)
    elif status_code == 429:
        return RateLimitedError(message)
    elif status_code >= 500:
        return UpstreamError(message, status_code=status_code)
    else:
        return UpstreamError(message, status_code=status_code)
