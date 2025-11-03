"""Configuration management for jankins MCP server.

Environment variables and CLI flags with proper precedence:
CLI flags > Environment variables > Defaults
"""

from typing import Literal, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class JankinsConfig(BaseSettings):
    """Configuration for jankins MCP server.

    Environment variables are prefixed with JENKINS_ or MCP_ to avoid conflicts.
    No .env file loading - configuration is explicit via env vars or CLI.
    """

    model_config = SettingsConfigDict(
        env_prefix="",
        case_sensitive=False,
        env_file=None,  # Explicitly disable .env loading
        extra="ignore",  # Ignore extra environment variables
    )

    # Jenkins connection
    jenkins_url: str = Field(
        ...,
        description="Jenkins server URL",
        validation_alias="JENKINS_URL"
    )
    jenkins_user: str = Field(
        ...,
        description="Jenkins username",
        validation_alias="JENKINS_USER"
    )
    jenkins_api_token: str = Field(
        ...,
        description="Jenkins API token",
        validation_alias="JENKINS_API_TOKEN"
    )

    # MCP transport
    mcp_transport: Literal["http", "sse", "stdio"] = Field(
        default="stdio",
        description="MCP transport type",
        validation_alias="MCP_TRANSPORT"
    )
    mcp_bind: str = Field(
        default="127.0.0.1:8080",
        description="MCP server bind address",
        validation_alias="MCP_BIND"
    )

    # Origin validation
    origin_enforce: bool = Field(
        default=False,
        description="Enforce Origin header validation",
        validation_alias="ORIGIN_ENFORCE"
    )
    origin_expected: Optional[str] = Field(
        default=None,
        description="Expected Origin header value",
        validation_alias="ORIGIN_EXPECTED"
    )

    # Logging
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(
        default="INFO",
        description="Logging level",
        validation_alias="LOG_LEVEL"
    )
    log_json: bool = Field(
        default=False,
        description="Use JSON structured logging",
        validation_alias="LOG_JSON"
    )
    debug_http: bool = Field(
        default=False,
        description="Log Jenkins HTTP requests/responses",
        validation_alias="DEBUG_HTTP"
    )

    # Log retrieval defaults
    log_max_lines_default: int = Field(
        default=2000,
        description="Default maximum log lines to retrieve",
        validation_alias="LOG_MAX_LINES_DEFAULT"
    )
    log_max_bytes_default: int = Field(
        default=262144,  # 256KB
        description="Default maximum log bytes to retrieve",
        validation_alias="LOG_MAX_BYTES_DEFAULT"
    )

    # Performance
    jenkins_timeout: int = Field(
        default=30,
        description="Jenkins API request timeout in seconds",
        validation_alias="JENKINS_TIMEOUT"
    )
    jenkins_retries: int = Field(
        default=3,
        description="Jenkins API retry attempts",
        validation_alias="JENKINS_RETRIES"
    )

    # Rate limiting
    rate_limit_enabled: bool = Field(
        default=True,
        description="Enable rate limiting",
        validation_alias="RATE_LIMIT_ENABLED"
    )
    rate_limit_per_minute: int = Field(
        default=60,
        description="Rate limit requests per minute per user",
        validation_alias="RATE_LIMIT_PER_MINUTE"
    )
    rate_limit_burst: int = Field(
        default=10,
        description="Rate limit burst size",
        validation_alias="RATE_LIMIT_BURST"
    )

    # Caching
    cache_enabled: bool = Field(
        default=False,
        description="Enable response caching",
        validation_alias="CACHE_ENABLED"
    )
    cache_ttl: int = Field(
        default=300,
        description="Cache TTL in seconds",
        validation_alias="CACHE_TTL"
    )

    @property
    def bind_host(self) -> str:
        """Extract host from bind address."""
        return self.mcp_bind.split(":")[0]

    @property
    def bind_port(self) -> int:
        """Extract port from bind address."""
        return int(self.mcp_bind.split(":")[1])
