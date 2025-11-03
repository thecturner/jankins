# jankins

**Token-optimized Jenkins MCP server with smart log handling and failure triage**

jankins provides MCP-compliant access to Jenkins with features designed for AI coding assistants:

- 🎯 **Token-aware formatting**: Summary/full/diff output modes minimize context usage
- 📊 **Smart log truncation**: Progressive retrieval with byte offsets, regex filtering, and ANSI cleanup
- 🔍 **Failure triage**: Automated root cause analysis with hypotheses and next steps
- ⚡ **Efficient by default**: Returns compact summaries unless full detail is requested
- 🛡️ **Better error handling**: Structured errors with remediation hints and correlation IDs
- 📝 **Built-in prompts**: Pre-built workflows for common CI/CD tasks

## Quick Start

### Installation

```bash
pip install -e .
```

### Basic Usage

```bash
# Set environment variables
export JENKINS_URL=https://jenkins.example.com
export JENKINS_USER=myuser
export JENKINS_API_TOKEN=11234567890abcdef1234567890abcdef

# Start the server
jankins

# Or use CLI flags
jankins --jenkins-url https://jenkins.example.com \
        --jenkins-user myuser \
        --jenkins-token $TOKEN \
        --bind 0.0.0.0:8080
```

### Generate Jenkins API Token

1. Log in to Jenkins
2. Click your username (top right) → Configure
3. Scroll to "API Token" section
4. Click "Add new Token"
5. Give it a name and click "Generate"
6. Copy the token (you won't see it again!)

## Configuration

Configuration via environment variables or CLI flags. CLI flags take precedence.

| CLI Flag | Env Variable | Default | Description |
|----------|--------------|---------|-------------|
| `--jenkins-url` | `JENKINS_URL` | *required* | Jenkins server URL |
| `--jenkins-user` | `JENKINS_USER` | *required* | Jenkins username |
| `--jenkins-token` | `JENKINS_API_TOKEN` | *required* | Jenkins API token |
| `--transport` | `MCP_TRANSPORT` | `stdio` | MCP transport (`stdio`, `http`, or `sse`) |
| `--bind` | `MCP_BIND` | `127.0.0.1:8080` | Server bind address (http/sse only) |
| `--origin-enforce` | `ORIGIN_ENFORCE` | `false` | Enforce Origin header validation |
| `--origin-expected` | `ORIGIN_EXPECTED` | `null` | Expected Origin value |
| `--log-level` | `LOG_LEVEL` | `INFO` | Log level (DEBUG/INFO/WARNING/ERROR) |
| `--log-json` | `LOG_JSON` | `false` | Use JSON structured logging |
| `--debug-http` | `DEBUG_HTTP` | `false` | Log Jenkins HTTP requests |
| `--log-max-lines` | `LOG_MAX_LINES_DEFAULT` | `2000` | Default max log lines |
| `--log-max-bytes` | `LOG_MAX_BYTES_DEFAULT` | `262144` | Default max log bytes (256KB) |
| `--timeout` | `JENKINS_TIMEOUT` | `30` | Jenkins request timeout (seconds) |

## MCP Tools

jankins provides 25+ MCP tools organized by category:

### Jobs

- **`list_jobs`**: List jobs with prefix filtering and pagination
- **`get_job`**: Get detailed job information
- **`trigger_build`**: Trigger a new build with parameters
- **`enable_job`** / **`disable_job`**: Enable or disable a job

### Builds

- **`get_build`**: Get build information (supports `number` or `"last"`)
- **`get_build_changes`**: Get SCM changes/commits for a build
- **`get_build_artifacts`**: List build artifacts

### Logs

- **`get_build_log`**: Get logs with smart truncation and filtering
  - Supports: `filter_regex`, `redact`, `start` byte offset, `max_bytes`
  - Returns summary by default with error counts and failing stages
- **`search_log`**: Search logs for pattern with context window

### SCM & Pipeline

- **`get_job_scm`**: Get job SCM configuration
- **`get_build_scm`**: Get SCM info (commit, branch) for a build

### Health & System

- **`whoami`**: Get current user info and permissions
- **`get_status`**: Jenkins version and queue depth
- **`summarize_queue`**: Compact build queue summary

### Advanced Analysis

- **`triage_failure`**: Analyze failed builds with:
  - Root cause hypotheses
  - Top error messages
  - Failing stages
  - Suspect commits
  - Recommended next steps

- **`compare_runs`**: Compare two builds for:
  - Duration differences
  - Result changes
  - Stage-level diffs (with Blue Ocean)

- **`get_pipeline_graph`**: Get pipeline visualization with stages, parallel execution, and timing (Blue Ocean)

- **`analyze_build_log`**: Analyze logs with build tool-specific parsers (Maven, Gradle, NPM) for detailed error analysis and recommendations

- **`retry_flaky_build`**: Retry flaky builds with configurable attempts and delays

### Test Results

- **`get_test_report`**: Get test results summary (JUnit, pytest, etc.)
- **`get_failed_tests`**: List failed tests with error details and stack traces
- **`compare_test_results`**: Compare test results between builds for regression detection
- **`detect_flaky_tests`**: Identify flaky tests across multiple builds

### Logs (Enhanced)

- **`tail_log_live`**: Poll-based live log tailing with progressive byte offsets

## Output Formats

All tools support `format` parameter:

- **`summary`** (default): Compact, token-efficient view
- **`full`**: Complete data with all fields
- **`diff`**: Differences only (for comparisons)
- **`ids`**: IDs and URLs only

Example:
```json
{
  "name": "list_jobs",
  "arguments": {
    "format": "summary",
    "page_size": 20
  }
}
```

## Built-in Prompts

jankins includes pre-built prompts for common workflows:

- **`investigate_failure`**: Full failure investigation workflow
- **`tail_errors`**: Show only warnings and errors from a build
- **`compare_builds`**: Compare two builds to find differences
- **`check_job_health`**: Check overall job health and stability
- **`trigger_with_params`**: Trigger parameterized build with guidance
- **`search_logs`**: Search logs for specific patterns

## Client Examples

### Claude Desktop (stdio mode - recommended)

Add to your MCP settings:

```json
{
  "mcpServers": {
    "jankins": {
      "command": "jankins",
      "env": {
        "JENKINS_URL": "https://jenkins.example.com",
        "JENKINS_USER": "myuser",
        "JENKINS_API_TOKEN": "your-token-here"
      }
    }
  }
}
```

The default `stdio` transport communicates via stdin/stdout, which is the standard for MCP clients like Claude Desktop.

### HTTP Mode (for HTTP-based MCP clients)

If your client requires HTTP transport:

```json
{
  "mcp": {
    "servers": {
      "jankins": {
        "url": "http://localhost:8080/mcp",
        "headers": {
          "Content-Type": "application/json"
        }
      }
    }
  }
}
```

### Direct HTTP Request

Start in HTTP mode:
```bash
jankins --transport http
```

Then make requests:
```bash
curl -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
      "name": "get_build",
      "arguments": {
        "name": "my-job",
        "number": "last",
        "format": "summary"
      }
    }
  }'
```

## Example Workflows

### Investigate a Failing Build

```
Use the "investigate_failure" prompt with job "backend-api"
```

This will:
1. Get build status
2. Retrieve error summary from logs
3. Perform failure triage
4. Show suspect commits
5. Provide recommended next steps

### Compare Two Builds

```json
{
  "name": "compare_runs",
  "arguments": {
    "name": "backend-api",
    "base": "100",
    "head": "101"
  }
}
```

### Search Logs for Error Pattern

```json
{
  "name": "search_log",
  "arguments": {
    "name": "backend-api",
    "pattern": "OutOfMemoryError",
    "window_lines": 10
  }
}
```

### Get Only Errors from Last Build

```json
{
  "name": "get_build_log",
  "arguments": {
    "name": "backend-api",
    "number": "last",
    "filter_regex": "ERROR|FATAL",
    "redact": true,
    "format": "summary"
  }
}
```

## Error Handling

jankins provides structured errors with:

- **Error code**: JSON-RPC compliant error codes
- **Correlation ID**: Track requests across logs
- **Hint**: Human-readable remediation hint
- **Next actions**: Specific steps to resolve the issue
- **Docs URL**: Link to troubleshooting guide

Error taxonomy:
- `InvalidParams` (-32602): Invalid tool parameters
- `Unauthorized` (-32001): Authentication failed
- `Forbidden` (-32002): Insufficient permissions
- `NotFound` (-32003): Resource not found
- `Timeout` (-32007): Request timed out
- `UpstreamError` (-32006): Jenkins server error

## Token Optimization

jankins minimizes token usage through:

1. **Default summaries**: Summary format by default, full on request
2. **Field limiting**: Only essential fields in summary mode
3. **Smart truncation**: Progressive log retrieval with byte limits
4. **Token estimation**: Responses include estimated token count
5. **Structured data**: Compact tables and lists over verbose text
6. **Metadata separation**: Performance data in `_meta` section

Example response structure:
```json
{
  "build_number": 42,
  "result": "FAILURE",
  "duration": "2m 15s",
  "_meta": {
    "correlation_id": "abc-123",
    "took_ms": 250,
    "format": "summary",
    "token_estimate": 180
  }
}
```

## Security

- **Explicit configuration**: Uses env vars or CLI flags (ignores .env files in working directory)
- **Basic auth**: Uses Jenkins API tokens (never passwords)
- **Optional Origin validation**: Enforce allowed origins
- **No secret logging**: Credentials are redacted in logs
- **Secret masking**: Jenkins secret masks are preserved/redacted

**Note**: jankins ignores any .env files in your working directory and only reads the specific environment variables it needs (JENKINS_*, MCP_*, etc.). This prevents conflicts with project .env files.

Generate API tokens:
```
Jenkins → User → Configure → API Token → Add new Token
```

## Health Checks

- `GET /_health`: Basic health check
- `GET /_ready`: Readiness check (verifies Jenkins connectivity)
- `GET /_metrics`: Placeholder for Prometheus metrics

## Development

### Run from Source

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run server
python -m jankins --jenkins-url $URL --jenkins-user $USER --jenkins-token $TOKEN

# With debug logging
python -m jankins --log-level DEBUG --debug-http
```

### Testing

```bash
pytest tests/
```

## Docker

See `docker-compose.yml` for local Jenkins + jankins setup.

```bash
docker-compose up
```

This starts:
- Jenkins LTS on port 8081
- jankins MCP server on port 8080

## Feature Comparison

| Feature | jankins | Official Plugin | Community Servers |
|---------|---------|----------------|-------------------|
| MCP Protocol | ✅ 2025-06-18 | ✅ | ⚠️ Varies |
| Token optimization | ✅ | ❌ | ❌ |
| Progressive logs | ✅ | ⚠️ Limited | ❌ |
| Failure triage | ✅ | ❌ | ❌ |
| Build comparison | ✅ | ❌ | ❌ |
| Structured errors | ✅ | ⚠️ Basic | ❌ |
| Built-in prompts | ✅ | ❌ | ❌ |
| Format modes | ✅ | ❌ | ❌ |
| Origin validation | ✅ | ✅ | ⚠️ Varies |

## Troubleshooting

### "Unauthorized" Error

- Verify `JENKINS_USER` and `JENKINS_API_TOKEN` are correct
- Regenerate API token from Jenkins user settings
- Check Jenkins server is accessible

### "Timeout" Error

- Increase `--timeout` value
- Check Jenkins server responsiveness
- Verify network connectivity

### "Tool not found" Error

- Ensure server started successfully
- Check MCP client configuration
- Verify tool name spelling

### Large Logs Timing Out

- Use `max_bytes` parameter to limit retrieval
- Use `filter_regex` to reduce log size
- Use `format=summary` for overview first

## License

MIT

## Contributing

Contributions welcome! Please:

1. Add tests for new features
2. Follow existing code style
3. Update documentation
4. Add type hints

## Acknowledgments

Built on:
- [python-jenkins](https://python-jenkins.readthedocs.io/) for Jenkins API
- [Model Context Protocol](https://modelcontextprotocol.io/) spec
- [Starlette](https://www.starlette.io/) for transport layer
