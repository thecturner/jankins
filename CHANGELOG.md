# Changelog

All notable changes to jankins will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.1] - 2025-01-XX

### Added
- **stdio transport**: Default MCP transport for communication via stdin/stdout
  - Standard for MCP clients like Claude Desktop
  - Logs to stderr to avoid protocol interference
  - Line-buffered JSON-RPC message handling

### Changed
- Default transport changed from `http` to `stdio`
- `--bind` parameter now only applies to http/sse transports

### Fixed
- Configuration now ignores extra environment variables from .env files in working directory
- Prevents "extra inputs are not allowed" error when starting from directories with project .env files

## [0.2.0] - 2025-01-XX

### Added
- **Blue Ocean API Integration**: Full support for Blue Ocean REST API
  - `get_pipeline_graph` tool for pipeline visualization with stages and parallel execution
  - Enhanced `compare_runs` with stage-level performance comparison
  - Detailed failing stage analysis with step-level information
- **Test Result Parsing**: Comprehensive test analysis capabilities
  - `get_test_report` tool for JUnit/pytest/etc test results
  - `get_failed_tests` tool with error details and stack traces
  - `compare_test_results` tool for test regression detection
  - `detect_flaky_tests` tool for identifying inconsistent tests across builds
- **Pluggable Build Tool Analyzers**: Smart log analysis for different build tools
  - Maven analyzer with dependency resolution and compilation error detection
  - Gradle analyzer with task execution and daemon crash detection
  - NPM/Yarn analyzer with module resolution and memory error detection
  - `analyze_build_log` tool with auto-detection and build tool-specific recommendations
- **Rate Limiting**: Token bucket-based rate limiting per user/IP
  - Configurable requests per minute and burst size
  - Automatic bucket cleanup to prevent memory leaks
  - Rate limit headers in responses (X-RateLimit-Limit, X-RateLimit-Remaining)
  - 429 responses with retry-after hints
- **Prometheus Metrics**: Comprehensive metrics collection and export
  - Request counts, durations, and success rates
  - Tool usage statistics and error tracking
  - Jenkins API call metrics
  - Rate limit hit tracking
  - `/\_metrics` endpoint with Prometheus text format
  - Percentile calculations (p50, p95, p99)
- **Live Log Tailing**: Poll-based log streaming
  - `tail_log_live` tool for incremental log retrieval
  - Progressive byte offset tracking for continuous updates
- **Retry Mechanism**: Automatic retry for flaky builds
  - `retry_flaky_build` tool with configurable max retries and delays
  - Detailed retry attempt tracking and success reporting
- **Response Caching**: In-memory cache for frequent requests
  - TTL-based expiration with configurable timeout
  - Size-limited cache with automatic eviction
  - Cache statistics and hit rate tracking
  - Selective caching for read-only operations

### Enhanced
- Extended configuration options for rate limiting and caching
- Improved error handling across all new tools
- Better token optimization for test results and analyzer output

### Performance
- Response caching reduces Jenkins API load
- Rate limiting prevents server overload
- Metrics tracking enables performance monitoring

## [0.1.0] - 2025-01-XX

### Added
- Initial release of jankins MCP server
- MCP protocol implementation (2025-06-18)
- Token-aware response formatting (summary/full/diff/ids modes)
- Progressive log retrieval with byte offsets
- Smart log filtering and redaction
- 15+ MCP tools for Jenkins operations:
  - Job management (list, get, trigger, enable/disable)
  - Build operations (get, changes, artifacts)
  - Log tools (get, search with progressive API)
  - SCM information retrieval
  - Health and status checks
  - Advanced failure triage
  - Build comparison
- 6 built-in prompt templates for common workflows
- Structured error handling with remediation hints
- Correlation IDs for request tracking
- HTTP and SSE transport support
- Configuration via CLI flags and environment variables
- Docker support with docker-compose setup
- Comprehensive test suite
- Token estimation and optimization
- Origin header validation (optional)
- Detailed logging with JSON support

### Features
- Feature parity with official Jenkins MCP plugin
- Superior log handling with progressive retrieval
- Advanced triage capabilities not available in other solutions
- Build comparison tool for regression analysis
- Token-optimized responses for AI assistants
- Extensive documentation and examples

[Unreleased]: https://github.com/thecturner/jankins/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/thecturner/jankins/releases/tag/v0.2.0
[0.1.0]: https://github.com/thecturner/jankins/releases/tag/v0.1.0
