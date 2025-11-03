# Security Policy

## Supported Versions

We release patches for security vulnerabilities for the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 0.2.x   | :white_check_mark: |
| 0.1.x   | :x:                |

## Reporting a Vulnerability

**Please do not report security vulnerabilities through public GitHub issues.**

Instead, please report them via email to: [security contact - add your email here]

You should receive a response within 48 hours. If for some reason you do not, please follow up via email to ensure we received your original message.

Please include the following information (as much as you can provide) to help us better understand the nature and scope of the possible issue:

* Type of issue (e.g. buffer overflow, SQL injection, cross-site scripting, etc.)
* Full paths of source file(s) related to the manifestation of the issue
* The location of the affected source code (tag/branch/commit or direct URL)
* Any special configuration required to reproduce the issue
* Step-by-step instructions to reproduce the issue
* Proof-of-concept or exploit code (if possible)
* Impact of the issue, including how an attacker might exploit it

This information will help us triage your report more quickly.

## Security Update Process

1. **Report Received**: Security reports are triaged within 48 hours
2. **Assessment**: We assess the impact and severity
3. **Fix Development**: A fix is developed in a private security fork
4. **Testing**: The fix is thoroughly tested
5. **Disclosure**:
   - A security advisory is published
   - A new release with the fix is published
   - CVE is requested if applicable

## Security Best Practices

When using jankins:

### Credential Management

* **Never hardcode credentials** in configuration files
* Use environment variables or secure secret management systems
* Rotate Jenkins API tokens regularly
* Use the principle of least privilege for Jenkins user permissions

### Network Security

* Use HTTPS for Jenkins URLs (never HTTP)
* Consider running jankins behind a firewall
* Use `--origin-enforce` flag to validate request origins
* Limit network access to jankins server

### Dependencies

* Keep jankins updated to the latest version
* Regularly update Python dependencies
* Monitor security advisories via GitHub Security Advisories
* Use `pip-audit` or `safety` to scan dependencies

### Deployment Security

* Run jankins with minimal required permissions
* Use containerization (Docker) for isolation
* Enable logging for audit trails
* Monitor logs for suspicious activity

### API Token Security

Generate Jenkins API tokens with minimal required permissions:

1. Log into Jenkins
2. Navigate to: User → Configure → API Token
3. Create a token with specific scope
4. Store securely (environment variable, secrets manager)
5. Never commit tokens to version control

### Secure Configuration

```bash
# Good - uses environment variables
export JENKINS_URL=https://jenkins.example.com
export JENKINS_USER=readonly-user
export JENKINS_API_TOKEN=$(vault read -field=token secret/jenkins)
jankins --origin-enforce --origin-expected https://jenkins.example.com

# Bad - credentials in command line (visible in process list)
jankins --jenkins-token mytoken123  # Don't do this!
```

### Rate Limiting

Configure rate limiting to prevent abuse:

```python
# In server configuration
config = JankinsConfig(
    rate_limit_enabled=True,
    rate_limit_requests_per_minute=60,
    rate_limit_burst_size=10
)
```

## Security Features

jankins includes several built-in security features:

* **Credential Redaction**: Automatic redaction of sensitive data in logs
* **Origin Validation**: Optional Origin header enforcement
* **Rate Limiting**: Token bucket rate limiting (v0.2.0+)
* **Secrets Detection**: Pre-commit hooks for detecting secrets
* **Dependency Scanning**: Automated scanning via Dependabot and Safety

## Known Security Considerations

### Jenkins Server Trust

jankins makes authenticated requests to your Jenkins server. Ensure:

* Your Jenkins server uses valid TLS certificates
* You trust the Jenkins server you're connecting to
* Network connection is secure (avoid public WiFi)

### Log Exposure

Build logs may contain sensitive information:

* Use the `redact` parameter to mask secrets
* Review logs before sharing
* Configure Jenkins secret masking

### MCP Transport Security

* **stdio transport**: Secure for local use
* **HTTP transport**: Use behind reverse proxy with TLS
* **SSE transport**: Requires proper CORS configuration

## Vulnerability Disclosure Timeline

We aim for the following timeline:

* **T+0**: Vulnerability reported
* **T+48h**: Initial response and triage
* **T+7d**: Impact assessment complete
* **T+30d**: Fix developed and tested
* **T+45d**: Public disclosure (if severity allows)

Critical vulnerabilities may have accelerated timelines.

## Security Advisories

Security advisories are published via:

* [GitHub Security Advisories](https://github.com/thecturner/jankins/security/advisories)
* Release notes in CHANGELOG.md
* PyPI release descriptions

## Acknowledgments

We appreciate the security research community's efforts in responsibly disclosing vulnerabilities. Contributors who report valid security issues will be acknowledged in:

* CHANGELOG.md
* GitHub Security Advisory
* Project README (with permission)

## Compliance

jankins is designed to help with:

* **SLSA Level 3**: Supply chain security via provenance
* **SBOM**: Software Bill of Materials generation
* **Dependency Transparency**: Regular dependency updates via Dependabot

## Contact

For security-related questions (not vulnerability reports):

* Open a GitHub Discussion
* Email: [security contact email]

For vulnerability reports, please follow the process above.

---

**Last Updated**: 2025-01-03
