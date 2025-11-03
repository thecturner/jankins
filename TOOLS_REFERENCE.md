# jankins Tools Reference Card

Complete reference for all 15+ MCP tools.

## Jobs (5 tools)

### `list_jobs`
List Jenkins jobs with filtering and pagination.

**Parameters:**
- `prefix` (string, optional): Job name prefix filter
- `page` (number, optional): Page number (default: 1)
- `page_size` (number, optional): Items per page (default: 50)
- `format` (string, optional): Output format (default: "summary")

**Example:**
```json
{
  "name": "list_jobs",
  "arguments": {
    "prefix": "backend",
    "page_size": 20,
    "format": "summary"
  }
}
```

---

### `get_job`
Get detailed information about a specific job.

**Parameters:**
- `name` (string, required): Full job name
- `format` (string, optional): Output format (default: "summary")

**Example:**
```json
{
  "name": "get_job",
  "arguments": {
    "name": "backend-api",
    "format": "summary"
  }
}
```

---

### `trigger_build`
Trigger a new build with optional parameters.

**Parameters:**
- `name` (string, required): Full job name
- `parameters` (object, optional): Build parameters as key-value pairs

**Example:**
```json
{
  "name": "trigger_build",
  "arguments": {
    "name": "backend-api",
    "parameters": {
      "BRANCH": "develop",
      "ENV": "staging"
    }
  }
}
```

---

### `enable_job`
Enable a Jenkins job to allow builds.

**Parameters:**
- `name` (string, required): Full job name

---

### `disable_job`
Disable a Jenkins job to prevent builds.

**Parameters:**
- `name` (string, required): Full job name

---

## Builds (3 tools)

### `get_build`
Get build information.

**Parameters:**
- `name` (string, required): Full job name
- `number` (string, optional): Build number or "last" (default: "last")
- `format` (string, optional): Output format (default: "summary")

**Example:**
```json
{
  "name": "get_build",
  "arguments": {
    "name": "backend-api",
    "number": "last",
    "format": "summary"
  }
}
```

---

### `get_build_changes`
Get SCM changes (commits) for a build.

**Parameters:**
- `name` (string, required): Full job name
- `number` (string, optional): Build number or "last" (default: "last")
- `format` (string, optional): Output format (default: "summary")

**Example:**
```json
{
  "name": "get_build_changes",
  "arguments": {
    "name": "backend-api"
  }
}
```

---

### `get_build_artifacts`
Get artifacts produced by a build.

**Parameters:**
- `name` (string, required): Full job name
- `number` (string, optional): Build number or "last" (default: "last")
- `format` (string, optional): Output format (default: "summary")

---

## Logs (2 tools)

### `get_build_log`
Get build log with smart truncation and filtering.

**Parameters:**
- `name` (string, required): Full job name
- `number` (string, optional): Build number or "last" (default: "last")
- `start` (number, optional): Starting byte offset (default: 0)
- `max_bytes` (number, optional): Maximum bytes to retrieve
- `filter_regex` (string, optional): Regex pattern to filter log lines
- `redact` (boolean, optional): Remove ANSI codes and secret masks (default: true)
- `format` (string, optional): Output format (default: "summary")

**Example - Get error summary:**
```json
{
  "name": "get_build_log",
  "arguments": {
    "name": "backend-api",
    "format": "summary"
  }
}
```

**Example - Get only errors:**
```json
{
  "name": "get_build_log",
  "arguments": {
    "name": "backend-api",
    "filter_regex": "ERROR|FATAL",
    "format": "full"
  }
}
```

---

### `search_log`
Search build log for pattern with context window.

**Parameters:**
- `name` (string, required): Full job name
- `number` (string, optional): Build number or "last" (default: "last")
- `pattern` (string, required): Regex pattern to search for
- `window_lines` (number, optional): Lines of context before/after match (default: 5)
- `max_bytes` (number, optional): Maximum bytes to search

**Example:**
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

---

## SCM (2 tools)

### `get_job_scm`
Get SCM configuration for a job.

**Parameters:**
- `name` (string, required): Full job name
- `format` (string, optional): Output format (default: "summary")

---

### `get_build_scm`
Get SCM info (commit, branch) for a build.

**Parameters:**
- `name` (string, required): Full job name
- `number` (string, optional): Build number or "last" (default: "last")

---

## Health & System (3 tools)

### `whoami`
Get current authenticated user information.

**Parameters:** None

**Example:**
```json
{
  "name": "whoami",
  "arguments": {}
}
```

---

### `get_status`
Get Jenkins server status and queue depth.

**Parameters:** None

---

### `summarize_queue`
Get compact summary of Jenkins build queue.

**Parameters:** None

**Returns:**
- Total queued builds
- Blocked/stuck counts
- Top 20 queue items

---

## Advanced Analysis (2 tools)

### `triage_failure`
Analyze failed build with root cause hypotheses.

**Parameters:**
- `name` (string, required): Full job name
- `number` (string, optional): Build number or "last" (default: "last")
- `max_bytes` (number, optional): Maximum log bytes to analyze
- `format` (string, optional): Output format (default: "summary")

**Returns:**
- Root cause hypotheses
- Top error messages
- Failing stages
- Suspect commits
- Recommended next steps

**Example:**
```json
{
  "name": "triage_failure",
  "arguments": {
    "name": "backend-api",
    "number": "last"
  }
}
```

---

### `compare_runs`
Compare two builds to identify differences.

**Parameters:**
- `name` (string, required): Full job name
- `base` (string, required): Base build number
- `head` (string, required): Head build number to compare
- `format` (string, optional): Output format (default: "diff")

**Returns:**
- Duration delta
- Result changes
- Stage differences

**Example:**
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

---

## Output Formats

All tools support `format` parameter (where applicable):

- **`summary`**: Compact, token-efficient (default)
- **`full`**: Complete data with all fields
- **`diff`**: Differences only (for comparisons)
- **`ids`**: IDs and URLs only

---

## Response Metadata

All tool responses include `_meta` section:

```json
{
  "result": { ... },
  "_meta": {
    "correlation_id": "abc-123",
    "took_ms": 250,
    "format": "summary",
    "token_estimate": 180
  }
}
```

---

## Common Patterns

### Check last build status
```json
{"name": "get_build", "arguments": {"name": "my-job"}}
```

### Get only errors from last build
```json
{
  "name": "get_build_log",
  "arguments": {
    "name": "my-job",
    "filter_regex": "ERROR|FATAL"
  }
}
```

### Investigate failure
```json
{"name": "triage_failure", "arguments": {"name": "my-job"}}
```

### Compare with previous build
```json
{
  "name": "compare_runs",
  "arguments": {
    "name": "my-job",
    "base": "99",
    "head": "100"
  }
}
```

### Search for specific error
```json
{
  "name": "search_log",
  "arguments": {
    "name": "my-job",
    "pattern": "NullPointerException"
  }
}
```

### Trigger parameterized build
```json
{
  "name": "trigger_build",
  "arguments": {
    "name": "deploy-job",
    "parameters": {"ENV": "prod", "VERSION": "v1.2.3"}
  }
}
```

---

## Error Responses

All errors follow MCP/JSON-RPC format:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "error": {
    "code": -32003,
    "message": "Job 'my-job' not found",
    "data": {
      "correlation_id": "abc-123",
      "hint": "Job not found or path is incorrect",
      "next_actions": [
        "Verify job name is correct",
        "Check job exists in Jenkins"
      ],
      "docs_url": "https://github.com/your-org/jankins#troubleshooting"
    }
  }
}
```

### Error Codes

- `-32602`: Invalid parameters
- `-32001`: Unauthorized (bad credentials)
- `-32002`: Forbidden (insufficient permissions)
- `-32003`: Not found (job/build doesn't exist)
- `-32007`: Timeout
- `-32006`: Upstream error (Jenkins server issue)

---

## Tips

1. **Use summary format** by default to minimize tokens
2. **Filter logs** with regex to reduce noise
3. **Triage failures** before diving into full logs
4. **Compare builds** to find regressions quickly
5. **Search logs** instead of scanning manually
6. **Check metadata** for token estimates
