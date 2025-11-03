"""CLI entrypoint for jankins MCP server."""

import sys
import asyncio
import click
import uvicorn
from typing import Optional

from .config import JankinsConfig
from .server import JankinsServer
from .mcp.stdio_transport import run_stdio_server


@click.command()
@click.option(
    "--jenkins-url",
    envvar="JENKINS_URL",
    required=True,
    help="Jenkins server URL (env: JENKINS_URL)"
)
@click.option(
    "--jenkins-user",
    envvar="JENKINS_USER",
    required=True,
    help="Jenkins username (env: JENKINS_USER)"
)
@click.option(
    "--jenkins-token",
    envvar="JENKINS_API_TOKEN",
    required=True,
    help="Jenkins API token (env: JENKINS_API_TOKEN)"
)
@click.option(
    "--transport",
    envvar="MCP_TRANSPORT",
    type=click.Choice(["http", "sse", "stdio"]),
    default="stdio",
    help="MCP transport type (env: MCP_TRANSPORT)"
)
@click.option(
    "--bind",
    envvar="MCP_BIND",
    default="127.0.0.1:8080",
    help="Server bind address (env: MCP_BIND)"
)
@click.option(
    "--origin-enforce/--no-origin-enforce",
    envvar="ORIGIN_ENFORCE",
    default=False,
    help="Enforce Origin header validation (env: ORIGIN_ENFORCE)"
)
@click.option(
    "--origin-expected",
    envvar="ORIGIN_EXPECTED",
    help="Expected Origin header value (env: ORIGIN_EXPECTED)"
)
@click.option(
    "--log-level",
    envvar="LOG_LEVEL",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"]),
    default="INFO",
    help="Logging level (env: LOG_LEVEL)"
)
@click.option(
    "--log-json/--no-log-json",
    envvar="LOG_JSON",
    default=False,
    help="Use JSON structured logging (env: LOG_JSON)"
)
@click.option(
    "--debug-http/--no-debug-http",
    envvar="DEBUG_HTTP",
    default=False,
    help="Log Jenkins HTTP requests (env: DEBUG_HTTP)"
)
@click.option(
    "--log-max-lines",
    envvar="LOG_MAX_LINES_DEFAULT",
    type=int,
    default=2000,
    help="Default max log lines (env: LOG_MAX_LINES_DEFAULT)"
)
@click.option(
    "--log-max-bytes",
    envvar="LOG_MAX_BYTES_DEFAULT",
    type=int,
    default=262144,
    help="Default max log bytes (env: LOG_MAX_BYTES_DEFAULT)"
)
@click.option(
    "--timeout",
    envvar="JENKINS_TIMEOUT",
    type=int,
    default=30,
    help="Jenkins API timeout in seconds (env: JENKINS_TIMEOUT)"
)
def main(
    jenkins_url: str,
    jenkins_user: str,
    jenkins_token: str,
    transport: str,
    bind: str,
    origin_enforce: bool,
    origin_expected: Optional[str],
    log_level: str,
    log_json: bool,
    debug_http: bool,
    log_max_lines: int,
    log_max_bytes: int,
    timeout: int,
):
    """jankins - Token-optimized Jenkins MCP server.

    Provides MCP-compliant access to Jenkins with smart log handling,
    failure triage, and token-aware formatting.

    Configuration via CLI flags or environment variables. CLI flags take precedence.

    Examples:

      # Start with environment variables
      export JENKINS_URL=https://jenkins.example.com
      export JENKINS_USER=myuser
      export JENKINS_API_TOKEN=mytoken
      jankins

      # Start with CLI flags
      jankins --jenkins-url https://jenkins.example.com \\
              --jenkins-user myuser \\
              --jenkins-token mytoken \\
              --bind 0.0.0.0:8080

      # Enable Origin validation
      jankins --origin-enforce --origin-expected https://jenkins.example.com
    """
    try:
        # Create config
        config = JankinsConfig(
            jenkins_url=jenkins_url,
            jenkins_user=jenkins_user,
            jenkins_api_token=jenkins_token,
            mcp_transport=transport,
            mcp_bind=bind,
            origin_enforce=origin_enforce,
            origin_expected=origin_expected,
            log_level=log_level,
            log_json=log_json,
            debug_http=debug_http,
            log_max_lines_default=log_max_lines,
            log_max_bytes_default=log_max_bytes,
            jenkins_timeout=timeout,
        )

        # Create server
        server = JankinsServer(config)

        # Handle stdio mode separately
        if config.mcp_transport == "stdio":
            # stdio mode - communicate via stdin/stdout
            # Log to stderr only
            click.echo(f"🚀 Starting jankins MCP server (stdio mode)", err=True)
            click.echo(f"   Jenkins: {config.jenkins_url}", err=True)
            click.echo(f"   Tools: {len(server.mcp_server.tools)}", err=True)
            click.echo(f"   Prompts: {len(server.mcp_server.prompts)}", err=True)
            click.echo(f"   Ready for JSON-RPC messages on stdin", err=True)
            click.echo(f"", err=True)

            # Run stdio server
            asyncio.run(run_stdio_server(server.mcp_server))
        else:
            # HTTP/SSE mode - start web server
            app = server.create_app()

            # Print startup info
            click.echo(f"🚀 Starting jankins MCP server", err=True)
            click.echo(f"   Jenkins: {config.jenkins_url}", err=True)
            click.echo(f"   Transport: {config.mcp_transport}", err=True)
            click.echo(f"   Bind: {config.mcp_bind}", err=True)
            click.echo(f"   Tools: {len(server.mcp_server.tools)}", err=True)
            click.echo(f"   Prompts: {len(server.mcp_server.prompts)}", err=True)
            click.echo(f"", err=True)
            click.echo(f"Endpoints:", err=True)
            click.echo(f"  POST http://{config.mcp_bind}/mcp", err=True)
            if config.mcp_transport == "sse":
                click.echo(f"  GET  http://{config.mcp_bind}/sse", err=True)
            click.echo(f"  GET  http://{config.mcp_bind}/_health", err=True)
            click.echo(f"", err=True)

            # Start server
            uvicorn.run(
                app,
                host=config.bind_host,
                port=config.bind_port,
                log_level=log_level.lower(),
                access_log=False,  # We handle logging ourselves
            )

    except KeyboardInterrupt:
        click.echo("\n👋 Shutting down gracefully...", err=True)
        sys.exit(0)
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
