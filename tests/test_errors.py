"""Test error handling."""

from jankins.errors import (
    JankinsError,
    InvalidParamsError,
    UnauthorizedError,
    NotFoundError,
    ErrorCode,
    map_http_error,
)


def test_jankins_error_creation():
    """Test basic JankinsError creation."""
    error = JankinsError(
        message="Test error",
        code=ErrorCode.INTERNAL_ERROR,
        hint="Test hint"
    )

    assert error.message == "Test error"
    assert error.code == ErrorCode.INTERNAL_ERROR
    assert error.hint == "Test hint"
    assert error.correlation_id is not None


def test_invalid_params_error():
    """Test InvalidParamsError."""
    error = InvalidParamsError("Missing parameter: name")

    assert error.code == ErrorCode.INVALID_PARAMS
    assert "parameter" in error.message.lower()


def test_unauthorized_error():
    """Test UnauthorizedError."""
    error = UnauthorizedError()

    assert error.code == ErrorCode.UNAUTHORIZED
    assert len(error.next_actions) > 0
    assert any("token" in action.lower() for action in error.next_actions)


def test_not_found_error():
    """Test NotFoundError."""
    error = NotFoundError("Job not found", resource_type="Job")

    assert error.code == ErrorCode.NOT_FOUND
    assert "job" in error.hint.lower()


def test_error_to_dict():
    """Test error serialization."""
    error = JankinsError(
        message="Test error",
        code=ErrorCode.TIMEOUT,
        hint="Test hint",
        next_actions=["Action 1", "Action 2"]
    )

    error_dict = error.to_dict()

    assert error_dict["code"] == ErrorCode.TIMEOUT.value
    assert error_dict["message"] == "Test error"
    assert error_dict["data"]["hint"] == "Test hint"
    assert len(error_dict["data"]["next_actions"]) == 2
    assert "correlation_id" in error_dict["data"]


def test_map_http_error():
    """Test HTTP error mapping."""
    # 401 -> Unauthorized
    error = map_http_error(401, "Unauthorized")
    assert isinstance(error, UnauthorizedError)

    # 404 -> NotFound
    error = map_http_error(404, "Not found")
    assert isinstance(error, NotFoundError)

    # 500 -> UpstreamError
    error = map_http_error(500, "Internal error")
    assert error.code == ErrorCode.UPSTREAM_ERROR
