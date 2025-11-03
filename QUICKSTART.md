# jankins Quick Start Guide

## Installation & First Run

```bash
# 1. Install
pip install -e .

# 2. Set credentials
export JENKINS_URL=https://jenkins.example.com
export JENKINS_USER=myuser
export JENKINS_API_TOKEN=your-token

# 3. Start server
jankins

# Server runs on http://127.0.0.1:8080
```

## Essential Tools (Quick Reference)

### Jobs
```json
{"name": "list_jobs", "arguments": {"format": "summary"}}
{"name": "get_job", "arguments": {"name": "my-job"}}
{"name": "trigger_build", "arguments": {"name": "my-job"}}
```

### Builds
```json
{"name": "get_build", "arguments": {"name": "my-job", "number": "last"}}
{"name": "get_build_changes", "arguments": {"name": "my-job"}}
```

### Logs
```json
{"name": "get_build_log", "arguments": {"name": "my-job", "format": "summary"}}
{"name": "search_log", "arguments": {"name": "my-job", "pattern": "ERROR"}}
```

### Advanced
```json
{"name": "triage_failure", "arguments": {"name": "my-job"}}
{"name": "compare_runs", "arguments": {"name": "my-job", "base": "100", "head": "101"}}
```

## Common Use Cases

### 1. Check Last Build Status
```bash
curl -X POST http://localhost:8080/mcp -d '{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "get_build",
    "arguments": {"name": "backend-api", "number": "last", "format": "summary"}
  }
}'
```

### 2. Investigate Failure
Use prompt: `investigate_failure` with job name

### 3. Get Only Errors from Log
```json
{
  "name": "get_build_log",
  "arguments": {
    "name": "my-job",
    "filter_regex": "ERROR|FATAL",
    "redact": true
  }
}
```

### 4. Compare Builds
```json
{
  "name": "compare_runs",
  "arguments": {
    "name": "my-job",
    "base": "100",
    "head": "101"
  }
}
```

## Output Formats

- `summary` - Default, compact (best for AI assistants)
- `full` - Complete data
- `diff` - Differences only
- `ids` - URLs and IDs only

Add to any tool: `"format": "summary"`

## Configuration Quick Reference

| What | How |
|------|-----|
| Jenkins URL | `--jenkins-url` or `JENKINS_URL` |
| Username | `--jenkins-user` or `JENKINS_USER` |
| API Token | `--jenkins-token` or `JENKINS_API_TOKEN` |
| Change port | `--bind 0.0.0.0:9000` |
| Debug logs | `--log-level DEBUG --debug-http` |
| JSON logs | `--log-json` |

## Testing Locally with Docker

```bash
# Start Jenkins + jankins
docker-compose up

# Jenkins: http://localhost:8081
# jankins: http://localhost:8080
```

## Troubleshooting

**"Unauthorized"**: Check `JENKINS_API_TOKEN` is correct
**"Timeout"**: Increase `--timeout 60`
**"Too many tokens"**: Use `format=summary` or reduce `max_bytes`

## MCP Client Setup

### Claude Desktop (stdio mode - default)
```json
{
  "mcpServers": {
    "jankins": {
      "command": "jankins",
      "env": {
        "JENKINS_URL": "https://jenkins.example.com",
        "JENKINS_USER": "user",
        "JENKINS_API_TOKEN": "token"
      }
    }
  }
}
```

jankins uses stdio transport by default, which is the standard for MCP clients.

### HTTP Mode (optional)
For HTTP-based clients, explicitly set transport:
```bash
jankins --transport http
```

## Getting Help

- Full docs: `README.md`
- CLI help: `jankins --help`
- Health check: `curl http://localhost:8080/_health`

## Next Steps

1. Try the built-in prompts (`investigate_failure`, `check_job_health`)
2. Explore all 25+ tools in README.md
3. Customize with your own prompts
4. Set up in your AI assistant (Claude, Copilot, etc.)
