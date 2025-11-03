# Monitoring Guide

This guide covers monitoring, observability, and alerting for jankins in production.

## Table of Contents

- [Metrics Overview](#metrics-overview)
- [Prometheus Integration](#prometheus-integration)
- [Grafana Dashboards](#grafana-dashboards)
- [Alerting](#alerting)
- [Log Aggregation](#log-aggregation)
- [Health Checks](#health-checks)
- [SLIs and SLOs](#slis-and-slos)

## Metrics Overview

jankins exposes Prometheus metrics at the `/_metrics` endpoint (when using HTTP/SSE transport).

### Available Metrics

#### Request Metrics

- `jankins_requests_total` - Total number of requests
  - Labels: `tool`, `status`
- `jankins_request_duration_ms` - Request duration in milliseconds
  - Labels: `tool`
- `jankins_requests_success` - Successful requests counter
- `jankins_requests_failed` - Failed requests counter
  - Labels: `error_type`

#### Jenkins API Metrics

- `jankins_jenkins_calls_total` - Total Jenkins API calls
  - Labels: `endpoint`
- `jankins_jenkins_call_duration_ms` - Jenkins API call duration
  - Labels: `endpoint`

#### Tool Usage Metrics

- `jankins_tool_usage` - Per-tool usage counter
  - Labels: `tool_name`

#### Error Metrics

- `jankins_errors_total` - Total errors
  - Labels: `error_type`

#### Cache Metrics

- `jankins_cache_hits` - Cache hit counter
- `jankins_cache_misses` - Cache miss counter
- `jankins_cache_size` - Current cache size
- `jankins_cache_hit_rate` - Cache hit rate (0-1)

#### Rate Limit Metrics

- `jankins_ratelimit_hits` - Rate limit hit counter
  - Labels: `user`

## Prometheus Integration

### Configuration

Add jankins to your Prometheus scrape configuration:

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'jankins'
    scrape_interval: 15s
    static_configs:
      - targets: ['localhost:8080']
    metrics_path: '/_metrics'
```

### Sample Queries

```promql
# Request rate (requests per second)
rate(jankins_requests_total[5m])

# Request duration 95th percentile
histogram_quantile(0.95, jankins_request_duration_ms)

# Error rate
rate(jankins_requests_failed[5m]) / rate(jankins_requests_total[5m])

# Top 5 most used tools
topk(5, sum by (tool) (jankins_tool_usage))

# Cache hit rate
jankins_cache_hits / (jankins_cache_hits + jankins_cache_misses)

# Rate limit violations
rate(jankins_ratelimit_hits[5m])
```

## Grafana Dashboards

### Dashboard: jankins Overview

**Panels:**

1. **Request Rate**
   ```promql
   sum(rate(jankins_requests_total[5m]))
   ```

2. **Success Rate**
   ```promql
   sum(rate(jankins_requests_success[5m])) / sum(rate(jankins_requests_total[5m])) * 100
   ```

3. **p50/p95/p99 Latency**
   ```promql
   histogram_quantile(0.50, jankins_request_duration_ms)
   histogram_quantile(0.95, jankins_request_duration_ms)
   histogram_quantile(0.99, jankins_request_duration_ms)
   ```

4. **Top Tools by Usage**
   ```promql
   topk(10, sum by (tool) (jankins_tool_usage))
   ```

5. **Error Rate by Type**
   ```promql
   sum by (error_type) (rate(jankins_errors_total[5m]))
   ```

6. **Cache Performance**
   ```promql
   # Hit rate
   jankins_cache_hits / (jankins_cache_hits + jankins_cache_misses)

   # Size
   jankins_cache_size
   ```

7. **Jenkins API Health**
   ```promql
   sum(rate(jankins_jenkins_calls_total[5m]))
   histogram_quantile(0.95, jankins_jenkins_call_duration_ms)
   ```

### Dashboard JSON

See `grafana-dashboard.json` in this directory for the complete dashboard definition.

## Alerting

### Recommended Alerts

#### High Error Rate

```yaml
- alert: JankinsHighErrorRate
  expr: |
    (sum(rate(jankins_requests_failed[5m])) / sum(rate(jankins_requests_total[5m]))) > 0.05
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "jankins error rate above 5%"
    description: "Error rate is {{ $value | humanizePercentage }}"
```

#### High Latency

```yaml
- alert: JankinsHighLatency
  expr: |
    histogram_quantile(0.95, jankins_request_duration_ms) > 5000
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "jankins p95 latency above 5s"
    description: "p95 latency is {{ $value }}ms"
```

#### Service Down

```yaml
- alert: JankinsDown
  expr: up{job="jankins"} == 0
  for: 1m
  labels:
    severity: critical
  annotations:
    summary: "jankins service is down"
```

#### Low Cache Hit Rate

```yaml
- alert: JankinsLowCacheHitRate
  expr: |
    jankins_cache_hits / (jankins_cache_hits + jankins_cache_misses) < 0.5
  for: 10m
  labels:
    severity: info
  annotations:
    summary: "jankins cache hit rate below 50%"
    description: "Cache hit rate is {{ $value | humanizePercentage }}"
```

#### Rate Limiting Active

```yaml
- alert: JankinsRateLimiting
  expr: rate(jankins_ratelimit_hits[5m]) > 0
  for: 5m
  labels:
    severity: info
  annotations:
    summary: "jankins is rate limiting requests"
    description: "{{ $value }} requests/s being rate limited"
```

## Log Aggregation

### Structured Logging

jankins supports JSON structured logging:

```bash
jankins --log-json --log-level INFO
```

### Log Fields

Standard fields in JSON logs:

```json
{
  "timestamp": "2025-01-03T12:00:00Z",
  "level": "INFO",
  "logger": "jankins.server",
  "message": "Request completed",
  "correlation_id": "abc-123",
  "tool": "get_build",
  "duration_ms": 150,
  "status": "success"
}
```

### Log Aggregation with ELK

**Filebeat configuration:**

```yaml
filebeat.inputs:
  - type: log
    enabled: true
    paths:
      - /var/log/jankins/*.log
    json.keys_under_root: true
    json.add_error_key: true

output.elasticsearch:
  hosts: ["elasticsearch:9200"]
  index: "jankins-%{+yyyy.MM.dd}"
```

### Log Aggregation with Loki

**Promtail configuration:**

```yaml
server:
  http_listen_port: 9080

positions:
  filename: /tmp/positions.yaml

clients:
  - url: http://loki:3100/loki/api/v1/push

scrape_configs:
  - job_name: jankins
    static_configs:
      - targets:
          - localhost
        labels:
          job: jankins
          __path__: /var/log/jankins/*.log
    pipeline_stages:
      - json:
          expressions:
            level: level
            correlation_id: correlation_id
            tool: tool
```

## Health Checks

### Endpoints

- `GET /_health` - Basic health check
  - Returns 200 if service is running
- `GET /_ready` - Readiness check
  - Returns 200 if service can accept requests
  - Verifies Jenkins connectivity

### Kubernetes Probes

```yaml
apiVersion: v1
kind: Pod
spec:
  containers:
    - name: jankins
      image: jankins:latest
      livenessProbe:
        httpGet:
          path: /_health
          port: 8080
        initialDelaySeconds: 10
        periodSeconds: 30
      readinessProbe:
        httpGet:
          path: /_ready
          port: 8080
        initialDelaySeconds: 5
        periodSeconds: 10
```

## SLIs and SLOs

### Service Level Indicators (SLIs)

1. **Availability**: Percentage of time service is up
   ```promql
   avg_over_time(up{job="jankins"}[30d])
   ```

2. **Error Rate**: Percentage of failed requests
   ```promql
   sum(rate(jankins_requests_failed[30d])) / sum(rate(jankins_requests_total[30d]))
   ```

3. **Latency**: p95 response time
   ```promql
   histogram_quantile(0.95, rate(jankins_request_duration_ms[30d]))
   ```

### Service Level Objectives (SLOs)

| SLI | SLO | Error Budget (30d) |
|-----|-----|-------------------|
| Availability | 99.5% | 3.6 hours |
| Error Rate | < 1% | 43,200 failed requests (at 1M req/month) |
| p95 Latency | < 2s | - |
| p99 Latency | < 5s | - |

### Monitoring Error Budget

```promql
# Availability error budget remaining (percentage)
(1 - (1 - avg_over_time(up{job="jankins"}[30d])) / (1 - 0.995)) * 100

# Error rate budget remaining
(1 - (sum(rate(jankins_requests_failed[30d])) / sum(rate(jankins_requests_total[30d]))) / 0.01) * 100
```

## Observability Best Practices

### 1. Use Correlation IDs

All jankins responses include a `correlation_id` in the `_meta` section. Use these to trace requests across logs and metrics.

### 2. Monitor Both Sides

- Monitor jankins metrics
- Monitor Jenkins server health
- Monitor network connectivity

### 3. Set Up Alerting Channels

```yaml
# alertmanager.yml
receivers:
  - name: 'jankins-alerts'
    slack_configs:
      - api_url: 'https://hooks.slack.com/services/...'
        channel: '#jankins-alerts'
        title: '{{ .GroupLabels.alertname }}'
        text: '{{ range .Alerts }}{{ .Annotations.description }}{{ end }}'
```

### 4. Regular Review

- Review dashboards weekly
- Update SLOs quarterly
- Test alerts monthly

## Troubleshooting with Metrics

### High Error Rate

1. Check error types:
   ```promql
   sum by (error_type) (rate(jankins_errors_total[5m]))
   ```

2. Identify failing tools:
   ```promql
   sum by (tool) (rate(jankins_requests_failed[5m]))
   ```

3. Check Jenkins connectivity:
   ```promql
   rate(jankins_jenkins_calls_total{endpoint="get_job_info"}[5m])
   ```

### High Latency

1. Check p95/p99 by tool:
   ```promql
   histogram_quantile(0.95, sum by (tool) (jankins_request_duration_ms))
   ```

2. Check Jenkins response times:
   ```promql
   histogram_quantile(0.95, jankins_jenkins_call_duration_ms)
   ```

3. Check cache performance:
   ```promql
   jankins_cache_hit_rate
   ```

### Memory Issues

1. Monitor cache size:
   ```promql
   jankins_cache_size
   ```

2. Check for memory leaks (requires process exporter):
   ```promql
   process_resident_memory_bytes{job="jankins"}
   ```

## Next Steps

- Set up [Grafana Dashboard](./grafana-dashboard.json)
- Configure [Alerting Rules](./alert-rules.yml)
- Review [Runbooks](./RUNBOOKS.md)
- Set up [Log Aggregation](#log-aggregation)
