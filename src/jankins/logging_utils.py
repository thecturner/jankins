"""Structured logging utilities with correlation IDs and context."""

import logging
import json
import time
from typing import Optional, Any
from contextvars import ContextVar
from datetime import datetime

# Context variable for correlation ID
correlation_id_var: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)


class StructuredFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add correlation ID if available
        correlation_id = correlation_id_var.get()
        if correlation_id:
            log_data["correlation_id"] = correlation_id

        # Add extra fields from record
        for key, value in record.__dict__.items():
            if key not in [
                "name", "msg", "args", "created", "filename", "funcName",
                "levelname", "levelno", "lineno", "module", "msecs",
                "message", "pathname", "process", "processName",
                "relativeCreated", "thread", "threadName", "exc_info",
                "exc_text", "stack_info"
            ]:
                log_data[key] = value

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data)


class ContextFilter(logging.Filter):
    """Add contextual information to log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Add correlation ID to record."""
        correlation_id = correlation_id_var.get()
        if correlation_id:
            record.correlation_id = correlation_id
        return True


def setup_logging(level: str = "INFO", use_json: bool = False) -> None:
    """Configure logging for jankins.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
        use_json: Use structured JSON logging
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create console handler
    handler = logging.StreamHandler()
    handler.setLevel(level)

    # Set formatter
    if use_json:
        formatter = StructuredFormatter()
    else:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

    handler.setFormatter(formatter)
    handler.addFilter(ContextFilter())
    root_logger.addHandler(handler)


class RequestLogger:
    """Context manager for logging requests with timing and correlation."""

    def __init__(self, logger: logging.Logger, tool_name: str, correlation_id: str):
        self.logger = logger
        self.tool_name = tool_name
        self.correlation_id = correlation_id
        self.start_time: Optional[float] = None

    def __enter__(self) -> "RequestLogger":
        """Start request logging."""
        correlation_id_var.set(self.correlation_id)
        self.start_time = time.time()
        self.logger.info(f"Starting {self.tool_name}", extra={
            "tool": self.tool_name,
            "event": "request_start"
        })
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """End request logging with timing."""
        took_ms = int((time.time() - self.start_time) * 1000) if self.start_time else 0

        if exc_type:
            self.logger.error(f"Failed {self.tool_name}", extra={
                "tool": self.tool_name,
                "event": "request_failed",
                "took_ms": took_ms,
                "error": str(exc_val)
            })
        else:
            self.logger.info(f"Completed {self.tool_name}", extra={
                "tool": self.tool_name,
                "event": "request_completed",
                "took_ms": took_ms
            })

        correlation_id_var.set(None)


def get_correlation_id() -> Optional[str]:
    """Get current correlation ID from context."""
    return correlation_id_var.get()


def set_correlation_id(correlation_id: str) -> None:
    """Set correlation ID in context."""
    correlation_id_var.set(correlation_id)
