# MCP Registry Submission for jankins

## For modelcontextprotocol/servers Registry

Submit this as a PR to: https://github.com/modelcontextprotocol/servers

### Add to `src/servers.json`:

```json
{
  "name": "jankins",
  "description": "Token-optimized Jenkins MCP server with smart log handling, failure triage, and advanced CI/CD analysis",
  "repository": "https://github.com/thecturner/jankins",
  "author": "thecturner",
  "license": "MIT",
  "categories": ["devtools", "ci-cd", "monitoring"],
  "install": {
    "type": "pip",
    "package": "jankins"
  },
  "config": {
    "env": {
      "JENKINS_URL": "Your Jenkins server URL",
      "JENKINS_USER": "Your Jenkins username",
      "JENKINS_API_TOKEN": "Your Jenkins API token"
    }
  },
  "features": [
    "25+ tools for Jenkins operations",
    "Blue Ocean pipeline visualization",
    "Test result parsing (JUnit, pytest, etc.)",
    "Build tool analyzers (Maven, Gradle, NPM)",
    "Smart log truncation with progressive retrieval",
    "Failure triage with root cause analysis",
    "Rate limiting and Prometheus metrics",
    "Response caching"
  ]
}
```

### Create README in `servers/src/jankins/` directory:

Copy the main README.md from the repository.

---

## For Smithery.ai Registry

Submit to: https://smithery.ai/

Fill out their submission form with:

**Name:** jankins
**Description:** Token-optimized Jenkins MCP server with smart log handling and advanced triage
**Repository:** https://github.com/thecturner/jankins
**Categories:** DevOps, CI/CD, Monitoring
**Installation:** `pip install jankins`

---

## For MCP Hub (mcp-get)

The mcp-get tool will automatically index from the official registry once accepted.

---

## For Glama.ai MCP Registry

Submit to: https://glama.ai/mcp/servers

Use GitHub integration to add the repository directly.

---

## Additional Promotion

1. **PyPI Publication:**
   ```bash
   python -m build
   twine upload dist/*
   ```

2. **Post on Social Media:**
   - Twitter/X with hashtags: #MCP #Jenkins #DevOps #CICD
   - LinkedIn developer communities
   - Reddit: r/devops, r/programming

3. **Write a Blog Post:**
   - Dev.to
   - Medium
   - Hashnode

4. **Submit to:**
   - Awesome MCP Servers lists on GitHub
   - Tool directories like ProductHunt
   - DevOps newsletters

5. **Add Topics to GitHub Repo:**
   - mcp-server
   - model-context-protocol
   - jenkins
   - ci-cd
   - devops
   - python
