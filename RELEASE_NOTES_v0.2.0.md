# jankins v0.2.0

Token-optimized Jenkins MCP server with 25+ tools for comprehensive CI/CD analysis and automation.

## 🎯 Key Features

### Blue Ocean API Integration
- Pipeline visualization with stages and parallel execution
- Stage-level performance comparison
- Detailed failing stage analysis with step-level information

### Test Result Analysis
- JUnit/pytest/etc test result parsing
- Failed test details with error messages and stack traces
- Test regression detection between builds
- Flaky test identification across multiple builds

### Build Tool Analyzers
- **Maven**: Dependency resolution, compilation errors, test failures
- **Gradle**: Task execution, daemon crashes, build tool issues
- **NPM/Yarn**: Module resolution, memory errors, package problems
- Auto-detection with build tool-specific recommendations

### Enterprise Features
- **Rate Limiting**: Token bucket algorithm per user/IP
- **Prometheus Metrics**: Comprehensive request and performance tracking
- **Response Caching**: In-memory cache with TTL for frequent requests
- **Live Log Tailing**: Progressive byte-offset streaming

### Reliability Tools
- Automated retry mechanism for flaky builds
- Smart failure triage with root cause hypotheses
- Build comparison for regression analysis

## 📦 Installation

```bash
pip install jankins
```

## ⚡ Quick Start

```bash
# Configure
export JENKINS_URL=https://jenkins.example.com
export JENKINS_USER=myuser
export JENKINS_API_TOKEN=your-token

# Run
jankins
```

Add to Claude Desktop:
```json
{
  "mcpServers": {
    "jankins": {
      "command": "jankins",
      "env": {
        "JENKINS_URL": "https://jenkins.example.com",
        "JENKINS_USER": "myuser",
        "JENKINS_API_TOKEN": "your-token"
      }
    }
  }
}
```

## 🛠️ Available Tools (25+)

- Job management (list, get, trigger, enable/disable)
- Build operations (get, changes, artifacts)
- Log analysis (progressive retrieval, search, filtering, live tailing)
- Test results (reports, failed tests, comparison, flaky detection)
- Pipeline graphs (Blue Ocean visualization)
- Build tool analysis (Maven, Gradle, NPM)
- Failure triage and comparison
- SCM information
- Health checks

## 📚 Documentation

- [README](https://github.com/thecturner/jankins#readme)
- [Quick Start Guide](https://github.com/thecturner/jankins/blob/master/QUICKSTART.md)
- [Tools Reference](https://github.com/thecturner/jankins/blob/master/TOOLS_REFERENCE.md)
- [Full Changelog](https://github.com/thecturner/jankins/blob/master/CHANGELOG.md)

## 🤝 Contributing

Contributions welcome! See [CONTRIBUTING.md](https://github.com/thecturner/jankins/blob/master/CONTRIBUTING.md)

## 📄 License

MIT License - see [LICENSE](https://github.com/thecturner/jankins/blob/master/LICENSE)
