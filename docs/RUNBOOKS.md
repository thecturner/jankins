# Runbooks

Operational runbooks for common jankins incidents and maintenance tasks.

## Table of Contents

- [Service Down](#service-down)
- [High Error Rate](#high-error-rate)
- [High Latency](#high-latency)
- [Memory Issues](#memory-issues)
- [Jenkins Connectivity Issues](#jenkins-connectivity-issues)
- [Rate Limiting Issues](#rate-limiting-issues)
- [Cache Problems](#cache-problems)
- [Deployment](#deployment)
- [Rollback](#rollback)

## Service Down

**Alert:** `JankinsDown`

**Severity:** Critical

### Symptoms

- Health check endpoint returns non-200
- No metrics being reported
- Users cannot access jankins

### Investigation

1. **Check if process is running**
   ```bash
   ps aux | grep jankins
   # or for systemd
   systemctl status jankins
   ```

2. **Check logs for crash**
   ```bash
   journalctl -u jankins -n 100
   # or
   tail -100 /var/log/jankins/jankins.log
   ```

3. **Check resource availability**
   ```bash
   df -h  # Disk space
   free -h  # Memory
   top  # CPU/Memory usage
   ```

### Resolution

1. **Restart the service**
   ```bash
   systemctl restart jankins
   # or
   docker restart jankins
   ```

2. **If restart fails, check configuration**
   ```bash
   jankins --help
   # Verify environment variables
   printenv | grep JENKINS
   ```

3. **Check Jenkins server connectivity**
   ```bash
   curl -u $JENKINS_USER:$JENKINS_API_TOKEN $JENKINS_URL/api/json
   ```

### Prevention

- Set up auto-restart (systemd `Restart=always`)
- Monitor resource usage
- Implement proper health checks

## High Error Rate

**Alert:** `JankinsHighErrorRate`

**Severity:** Warning

### Symptoms

- Error rate > 5% for 5 minutes
- Users report failures
- Increased error logs

### Investigation

1. **Identify error types**
   ```bash
   # From Prometheus
   sum by (error_type) (rate(jankins_errors_total[5m]))
   ```

2. **Check logs for patterns**
   ```bash
   grep ERROR /var/log/jankins/jankins.log | tail -100
   ```

3. **Identify failing tools**
   ```bash
   # From Prometheus
   sum by (tool) (rate(jankins_requests_failed[5m]))
   ```

### Resolution by Error Type

#### Unauthorized (401)

- **Cause**: Invalid Jenkins credentials
- **Fix**: Verify and update `JENKINS_API_TOKEN`
  ```bash
  export JENKINS_API_TOKEN=<new_token>
  systemctl restart jankins
  ```

#### NotFound (404)

- **Cause**: Job/build doesn't exist
- **Fix**: Verify job names are correct; may be user error

#### Timeout (408)

- **Cause**: Jenkins server slow or unresponsive
- **Fix**: Increase timeout or investigate Jenkins performance
  ```bash
  jankins --timeout 60
  ```

#### UpstreamError (500)

- **Cause**: Jenkins server error
- **Fix**: Check Jenkins server health and logs

### Prevention

- Set up Jenkins monitoring
- Implement circuit breakers
- Add retry logic for transient errors

## High Latency

**Alert:** `JankinsHighLatency`

**Severity:** Warning

### Symptoms

- p95 latency > 5 seconds
- Users report slow responses
- Increased queue depth

### Investigation

1. **Check per-tool latency**
   ```promql
   histogram_quantile(0.95, sum by (tool) (jankins_request_duration_ms))
   ```

2. **Check Jenkins API latency**
   ```promql
   histogram_quantile(0.95, jankins_jenkins_call_duration_ms)
   ```

3. **Check cache performance**
   ```promql
   jankins_cache_hit_rate
   ```

4. **Check resource utilization**
   ```bash
   top
   iotop
   ```

### Resolution

1. **If Jenkins is slow**
   - Investigate Jenkins server performance
   - Increase jankins timeout
   - Enable/tune caching

2. **If cache hit rate is low**
   - Increase cache size
   - Increase TTL
   ```python
   # In configuration
   cache_size = 1000  # Increase from 100
   cache_ttl = 300    # Increase from 60
   ```

3. **If CPU/Memory bound**
   - Scale horizontally (add instances)
   - Optimize queries
   - Use format=summary by default

### Prevention

- Enable response caching
- Monitor Jenkins performance
- Set appropriate timeouts
- Use CDN for static assets

## Memory Issues

**Alert:** Process memory high

**Severity:** Warning

### Symptoms

- Increasing memory usage
- OOM kills
- Slow performance

### Investigation

1. **Check memory usage**
   ```bash
   ps aux | grep jankins
   free -h
   ```

2. **Check cache size**
   ```promql
   jankins_cache_size
   ```

3. **Check for memory leaks**
   ```bash
   # Python memory profiler
   pip install memory_profiler
   python -m memory_profiler -m jankins
   ```

### Resolution

1. **Reduce cache size**
   ```python
   cache_max_size = 100  # Reduce if necessary
   ```

2. **Enable cache cleanup**
   - Ensure old entries are being cleaned up
   - Check TTL settings

3. **Restart service**
   ```bash
   systemctl restart jankins
   ```

4. **Increase memory limits** (if legitimate usage)
   ```bash
   # systemd
   [Service]
   MemoryLimit=2G
   ```

### Prevention

- Set memory limits
- Monitor memory trends
- Implement cache eviction
- Regular restarts if needed

## Jenkins Connectivity Issues

**Symptoms**

- Timeout errors
- Connection refused
- SSL/TLS errors

### Investigation

1. **Test connectivity**
   ```bash
   curl -v $JENKINS_URL
   ```

2. **Check DNS resolution**
   ```bash
   nslookup jenkins.example.com
   ```

3. **Check network connectivity**
   ```bash
   ping jenkins.example.com
   traceroute jenkins.example.com
   ```

4. **Verify credentials**
   ```bash
   curl -u $JENKINS_USER:$JENKINS_API_TOKEN $JENKINS_URL/api/json
   ```

### Resolution

1. **If DNS issue**
   - Update DNS configuration
   - Use IP address temporarily

2. **If network issue**
   - Check firewall rules
   - Verify network connectivity
   - Check proxy settings

3. **If SSL/TLS issue**
   - Verify certificate validity
   - Update CA certificates
   ```bash
   update-ca-certificates
   ```

4. **If authentication issue**
   - Regenerate API token
   - Verify user permissions

## Rate Limiting Issues

**Alert:** `JankinsRateLimiting`

**Severity:** Info

### Symptoms

- 429 Too Many Requests errors
- Users report intermittent failures
- Rate limit counter increasing

### Investigation

1. **Check rate limit hits**
   ```promql
   rate(jankins_ratelimit_hits[5m])
   ```

2. **Identify users hitting limits**
   ```promql
   sum by (user) (jankins_ratelimit_hits)
   ```

3. **Check logs**
   ```bash
   grep "rate limit" /var/log/jankins/jankins.log
   ```

### Resolution

1. **If legitimate traffic spike**
   - Increase rate limits temporarily
   ```python
   rate_limit_requests_per_minute = 120  # Increase from 60
   rate_limit_burst_size = 20  # Increase from 10
   ```

2. **If abuse**
   - Identify and block malicious users
   - Implement stricter limits
   - Add IP-based filtering

3. **If misconfigured limits**
   - Adjust based on actual usage patterns
   - Consider different limits per user type

### Prevention

- Monitor rate limit usage trends
- Set appropriate limits for usage patterns
- Implement graduated rate limiting
- Communicate limits to users

## Cache Problems

### Symptoms

- Low cache hit rate
- Cache size growing unbounded
- Stale data being served

### Investigation

1. **Check cache stats**
   ```promql
   jankins_cache_hit_rate
   jankins_cache_size
   ```

2. **Review cache configuration**
   ```python
   # Check current settings
   cache_ttl_seconds
   cache_max_size
   ```

### Resolution

1. **If hit rate too low**
   - Increase TTL
   - Increase cache size
   - Review what's being cached

2. **If serving stale data**
   - Reduce TTL
   - Implement cache invalidation
   - Clear cache manually:
   ```bash
   curl -X POST http://localhost:8080/_cache/clear
   ```

3. **If cache too large**
   - Reduce max size
   - Reduce TTL
   - Implement LRU eviction

## Deployment

### Standard Deployment

1. **Pre-deployment checks**
   ```bash
   # Run tests
   pytest

   # Check linting
   ruff check src tests

   # Security scan
   bandit -r src
   ```

2. **Build new version**
   ```bash
   # Build distributions
   python -m build

   # Or build Docker image
   docker build -t jankins:v0.3.0 .
   ```

3. **Deploy**
   ```bash
   # Using pip
   pip install --upgrade jankins==0.3.0

   # Using Docker
   docker pull jankins:v0.3.0
   docker stop jankins
   docker rm jankins
   docker run -d --name jankins jankins:v0.3.0

   # Using systemd
   systemctl restart jankins
   ```

4. **Post-deployment checks**
   ```bash
   # Health check
   curl http://localhost:8080/_health

   # Verify version
   curl http://localhost:8080/_metrics | grep version

   # Check logs
   journalctl -u jankins -f
   ```

### Blue-Green Deployment

1. **Deploy to green environment**
2. **Run smoke tests**
3. **Switch traffic** (load balancer/DNS)
4. **Monitor for issues**
5. **Keep blue environment for quick rollback**

## Rollback

### Quick Rollback

1. **Using pip**
   ```bash
   pip install jankins==0.2.1  # Previous version
   systemctl restart jankins
   ```

2. **Using Docker**
   ```bash
   docker stop jankins
   docker rm jankins
   docker run -d --name jankins jankins:v0.2.1
   ```

3. **Using git (source deployment)**
   ```bash
   git checkout v0.2.1
   pip install -e .
   systemctl restart jankins
   ```

### Post-Rollback

1. **Verify health**
   ```bash
   curl http://localhost:8080/_health
   ```

2. **Check metrics**
   - Error rate should decrease
   - Latency should normalize

3. **Investigate root cause**
   - Review logs from failed deployment
   - Analyze error patterns
   - Update runbook with findings

## Escalation

If issue persists after following runbook:

1. **Gather information**
   - Recent changes
   - Error logs
   - Metrics snapshots
   - Configuration

2. **Create incident**
   - Document timeline
   - Record actions taken
   - Note any workarounds

3. **Contact maintainers**
   - GitHub issue with [INCIDENT] tag
   - Include all gathered information

## Maintenance Tasks

### Weekly

- Review error logs
- Check disk space
- Verify backups
- Review metrics trends

### Monthly

- Update dependencies
- Review and update rate limits
- Capacity planning review
- Test disaster recovery

### Quarterly

- Security audit
- Performance review
- SLO review
- Runbook updates
