# 040 - Monitoring Setup

## Metadata

```yaml
prompt_id: "040"
phase: 6
agent: "@infrastructure"
model: "sonnet 4.5"
priority: P1
estimated_effort: "3 days"
dependencies: ["038", "039"]
```

## Objective

Implement comprehensive monitoring with Prometheus and Grafana.

## Task Description

Set up monitoring infrastructure with metrics collection, visualization, and alerting.

## Requirements

### Backend Metrics

```python
# backend/app/middleware/metrics.py
from prometheus_client import Counter, Histogram, Gauge, generate_latest
from flask import request, g, Response
import time

# Define metrics
REQUEST_COUNT = Counter(
    'novasight_http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

REQUEST_LATENCY = Histogram(
    'novasight_http_request_duration_seconds',
    'HTTP request latency',
    ['method', 'endpoint'],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

ACTIVE_REQUESTS = Gauge(
    'novasight_http_requests_in_progress',
    'Number of requests in progress',
    ['method']
)

# Query metrics
QUERY_EXECUTION_TIME = Histogram(
    'novasight_query_execution_seconds',
    'Query execution time',
    ['query_type', 'datasource_type'],
    buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0]
)

QUERY_RESULT_SIZE = Histogram(
    'novasight_query_result_rows',
    'Number of rows returned by queries',
    ['query_type'],
    buckets=[10, 100, 1000, 10000, 100000, 1000000]
)

# Template engine metrics
TEMPLATE_GENERATION_TIME = Histogram(
    'novasight_template_generation_seconds',
    'Template generation time',
    ['template_type']
)

TEMPLATE_VALIDATION_ERRORS = Counter(
    'novasight_template_validation_errors_total',
    'Template validation errors',
    ['template_type', 'error_type']
)

# Tenant metrics
ACTIVE_TENANTS = Gauge(
    'novasight_active_tenants',
    'Number of active tenants'
)

USERS_PER_TENANT = Gauge(
    'novasight_users_per_tenant',
    'Number of users per tenant',
    ['tenant_id']
)


def setup_metrics(app):
    """Setup metrics middleware."""
    
    @app.before_request
    def before_request():
        g.start_time = time.time()
        ACTIVE_REQUESTS.labels(method=request.method).inc()
    
    @app.after_request
    def after_request(response):
        if hasattr(g, 'start_time'):
            latency = time.time() - g.start_time
            endpoint = request.endpoint or 'unknown'
            
            REQUEST_COUNT.labels(
                method=request.method,
                endpoint=endpoint,
                status=response.status_code
            ).inc()
            
            REQUEST_LATENCY.labels(
                method=request.method,
                endpoint=endpoint
            ).observe(latency)
        
        ACTIVE_REQUESTS.labels(method=request.method).dec()
        return response
    
    @app.route('/metrics')
    def metrics():
        return Response(
            generate_latest(),
            mimetype='text/plain'
        )
```

### Prometheus Configuration

```yaml
# monitoring/prometheus/prometheus.yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

alerting:
  alertmanagers:
    - static_configs:
        - targets:
            - alertmanager:9093

rule_files:
  - /etc/prometheus/rules/*.yaml

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  - job_name: 'novasight-backend'
    kubernetes_sd_configs:
      - role: pod
        namespaces:
          names: ['novasight']
    relabel_configs:
      - source_labels: [__meta_kubernetes_pod_label_app_kubernetes_io_component]
        action: keep
        regex: backend
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
        action: keep
        regex: "true"
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_port]
        action: replace
        target_label: __address__
        regex: (.+)
        replacement: $1:9090

  - job_name: 'clickhouse'
    static_configs:
      - targets: ['clickhouse:9363']

  - job_name: 'redis'
    static_configs:
      - targets: ['redis:9121']

  - job_name: 'postgresql'
    static_configs:
      - targets: ['postgres-exporter:9187']
```

### Alert Rules

```yaml
# monitoring/prometheus/rules/novasight.yaml
groups:
  - name: novasight.rules
    rules:
      # High error rate
      - alert: HighErrorRate
        expr: |
          sum(rate(novasight_http_requests_total{status=~"5.."}[5m])) /
          sum(rate(novasight_http_requests_total[5m])) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: High error rate detected
          description: "Error rate is {{ $value | humanizePercentage }}"

      # High latency
      - alert: HighLatency
        expr: |
          histogram_quantile(0.95, 
            sum(rate(novasight_http_request_duration_seconds_bucket[5m])) by (le)
          ) > 2
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: High API latency
          description: "P95 latency is {{ $value | humanizeDuration }}"

      # Query timeout
      - alert: SlowQueries
        expr: |
          histogram_quantile(0.95,
            sum(rate(novasight_query_execution_seconds_bucket[5m])) by (le, datasource_type)
          ) > 30
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: Slow query performance
          description: "P95 query time for {{ $labels.datasource_type }} is {{ $value | humanizeDuration }}"

      # Template validation errors
      - alert: TemplateValidationErrors
        expr: |
          increase(novasight_template_validation_errors_total[1h]) > 10
        for: 15m
        labels:
          severity: warning
        annotations:
          summary: Template validation errors increasing
          description: "{{ $value }} validation errors in last hour"

      # Pod health
      - alert: BackendPodDown
        expr: |
          kube_deployment_status_replicas_available{deployment="backend"} /
          kube_deployment_spec_replicas{deployment="backend"} < 0.5
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: Backend pods unhealthy
          description: "Only {{ $value | humanizePercentage }} of pods available"
```

### Grafana Dashboards

```json
// monitoring/grafana/dashboards/novasight-overview.json
{
  "dashboard": {
    "title": "NovaSight Overview",
    "uid": "novasight-overview",
    "panels": [
      {
        "title": "Request Rate",
        "type": "graph",
        "gridPos": { "x": 0, "y": 0, "w": 12, "h": 8 },
        "targets": [
          {
            "expr": "sum(rate(novasight_http_requests_total[5m])) by (status)",
            "legendFormat": "{{status}}"
          }
        ]
      },
      {
        "title": "Error Rate",
        "type": "gauge",
        "gridPos": { "x": 12, "y": 0, "w": 6, "h": 4 },
        "targets": [
          {
            "expr": "sum(rate(novasight_http_requests_total{status=~\"5..\"}[5m])) / sum(rate(novasight_http_requests_total[5m]))"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "unit": "percentunit",
            "thresholds": {
              "mode": "absolute",
              "steps": [
                { "color": "green", "value": null },
                { "color": "yellow", "value": 0.01 },
                { "color": "red", "value": 0.05 }
              ]
            }
          }
        }
      },
      {
        "title": "P95 Latency",
        "type": "stat",
        "gridPos": { "x": 18, "y": 0, "w": 6, "h": 4 },
        "targets": [
          {
            "expr": "histogram_quantile(0.95, sum(rate(novasight_http_request_duration_seconds_bucket[5m])) by (le))"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "unit": "s"
          }
        }
      },
      {
        "title": "Active Tenants",
        "type": "stat",
        "gridPos": { "x": 12, "y": 4, "w": 6, "h": 4 },
        "targets": [
          {
            "expr": "novasight_active_tenants"
          }
        ]
      },
      {
        "title": "Query Execution Time",
        "type": "heatmap",
        "gridPos": { "x": 0, "y": 8, "w": 12, "h": 8 },
        "targets": [
          {
            "expr": "sum(increase(novasight_query_execution_seconds_bucket[5m])) by (le)",
            "format": "heatmap"
          }
        ]
      },
      {
        "title": "Template Generation Time",
        "type": "graph",
        "gridPos": { "x": 12, "y": 8, "w": 12, "h": 8 },
        "targets": [
          {
            "expr": "histogram_quantile(0.95, sum(rate(novasight_template_generation_seconds_bucket[5m])) by (le, template_type))",
            "legendFormat": "{{template_type}}"
          }
        ]
      }
    ]
  }
}
```

### ServiceMonitor

```yaml
# monitoring/prometheus/servicemonitor.yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: novasight-backend
  namespace: novasight
  labels:
    app.kubernetes.io/name: novasight
spec:
  selector:
    matchLabels:
      app.kubernetes.io/name: backend
  endpoints:
    - port: metrics
      interval: 15s
      path: /metrics
  namespaceSelector:
    matchNames:
      - novasight
```

## Expected Output

```
monitoring/
├── prometheus/
│   ├── prometheus.yaml
│   ├── servicemonitor.yaml
│   └── rules/
│       ├── novasight.yaml
│       ├── infrastructure.yaml
│       └── database.yaml
├── grafana/
│   ├── provisioning/
│   │   ├── dashboards/
│   │   │   └── dashboards.yaml
│   │   └── datasources/
│   │       └── datasources.yaml
│   └── dashboards/
│       ├── novasight-overview.json
│       ├── api-performance.json
│       ├── query-analytics.json
│       └── tenant-metrics.json
└── alertmanager/
    └── alertmanager.yaml
```

## Acceptance Criteria

- [ ] Prometheus scrapes all services
- [ ] Custom metrics exposed
- [ ] Alert rules fire correctly
- [ ] Grafana dashboards work
- [ ] Query performance tracked
- [ ] Template metrics captured
- [ ] Per-tenant metrics available
- [ ] Alert routing configured

## Reference Documents

- [Infrastructure Agent](../agents/infrastructure-agent.agent.md)
- [Helm Charts](./039-helm-charts.md)
