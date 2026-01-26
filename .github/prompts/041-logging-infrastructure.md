# 041 - Logging Infrastructure

## Metadata

```yaml
prompt_id: "041"
phase: 6
agent: "@infrastructure"
model: "sonnet 4.5"
priority: P1
estimated_effort: "2 days"
dependencies: ["040"]
```

## Objective

Implement structured logging with centralized log aggregation.

## Task Description

Set up structured logging with ELK/Loki stack for log aggregation and analysis.

## Requirements

### Structured Logger

```python
# backend/app/utils/logger.py
import logging
import json
import sys
from datetime import datetime
from flask import request, g
from typing import Optional, Dict, Any

class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        # Add request context if available
        if hasattr(g, 'request_id'):
            log_entry['request_id'] = g.request_id
        if hasattr(g, 'tenant'):
            log_entry['tenant_id'] = str(g.tenant.id)
        if hasattr(g, 'current_user_id'):
            log_entry['user_id'] = str(g.current_user_id)
        
        # Add extra fields
        if hasattr(record, 'extra'):
            log_entry.update(record.extra)
        
        # Add exception info
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_entry)


class ContextLogger:
    """Logger with context support."""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
    
    def _log(self, level: int, message: str, **kwargs):
        extra = {'extra': kwargs}
        self.logger.log(level, message, extra=extra)
    
    def debug(self, message: str, **kwargs):
        self._log(logging.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs):
        self._log(logging.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        self._log(logging.WARNING, message, **kwargs)
    
    def error(self, message: str, **kwargs):
        self._log(logging.ERROR, message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        self._log(logging.CRITICAL, message, **kwargs)
    
    def exception(self, message: str, **kwargs):
        self._log(logging.ERROR, message, exc_info=True, **kwargs)


def setup_logging(app):
    """Configure logging for the application."""
    
    # Get log level from config
    log_level = app.config.get('LOG_LEVEL', 'INFO')
    
    # Configure root logger
    root = logging.getLogger()
    root.setLevel(log_level)
    
    # Remove default handlers
    for handler in root.handlers[:]:
        root.removeHandler(handler)
    
    # Add JSON handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    root.addHandler(handler)
    
    # Suppress noisy loggers
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    
    return ContextLogger('novasight')


def get_logger(name: str) -> ContextLogger:
    """Get a logger for a module."""
    return ContextLogger(f'novasight.{name}')


# Usage example
# logger = get_logger('datasource')
# logger.info('Data source created', datasource_id='uuid', type='postgresql')
```

### Request Logging Middleware

```python
# backend/app/middleware/request_logging.py
import uuid
import time
from flask import request, g
from app.utils.logger import get_logger

logger = get_logger('http')

def setup_request_logging(app):
    """Setup request/response logging."""
    
    @app.before_request
    def before_request():
        # Generate unique request ID
        g.request_id = str(uuid.uuid4())[:8]
        g.start_time = time.time()
        
        # Log request
        logger.info(
            'Request started',
            request_id=g.request_id,
            method=request.method,
            path=request.path,
            query_string=request.query_string.decode(),
            remote_addr=request.remote_addr,
            user_agent=request.user_agent.string,
        )
    
    @app.after_request
    def after_request(response):
        duration = time.time() - g.start_time
        
        # Log response
        logger.info(
            'Request completed',
            request_id=g.request_id,
            method=request.method,
            path=request.path,
            status_code=response.status_code,
            duration_ms=round(duration * 1000, 2),
            content_length=response.content_length,
        )
        
        # Add request ID to response headers
        response.headers['X-Request-ID'] = g.request_id
        
        return response
    
    @app.errorhandler(Exception)
    def handle_exception(e):
        logger.exception(
            'Unhandled exception',
            request_id=getattr(g, 'request_id', 'unknown'),
            error_type=type(e).__name__,
            error_message=str(e),
        )
        raise e
```

### Loki Configuration

```yaml
# logging/loki/loki-config.yaml
auth_enabled: false

server:
  http_listen_port: 3100

ingester:
  lifecycler:
    ring:
      kvstore:
        store: inmemory
      replication_factor: 1
  chunk_idle_period: 5m
  chunk_retain_period: 30s

schema_config:
  configs:
    - from: 2024-01-01
      store: boltdb-shipper
      object_store: filesystem
      schema: v12
      index:
        prefix: index_
        period: 24h

storage_config:
  boltdb_shipper:
    active_index_directory: /loki/index
    cache_location: /loki/cache
    shared_store: filesystem
  filesystem:
    directory: /loki/chunks

limits_config:
  enforce_metric_name: false
  reject_old_samples: true
  reject_old_samples_max_age: 168h
  ingestion_rate_mb: 4
  ingestion_burst_size_mb: 6

chunk_store_config:
  max_look_back_period: 168h

table_manager:
  retention_deletes_enabled: true
  retention_period: 2160h  # 90 days
```

### Promtail Configuration

```yaml
# logging/promtail/promtail-config.yaml
server:
  http_listen_port: 9080
  grpc_listen_port: 0

positions:
  filename: /tmp/positions.yaml

clients:
  - url: http://loki:3100/loki/api/v1/push

scrape_configs:
  - job_name: kubernetes-pods
    kubernetes_sd_configs:
      - role: pod
    pipeline_stages:
      - json:
          expressions:
            timestamp: timestamp
            level: level
            message: message
            request_id: request_id
            tenant_id: tenant_id
            user_id: user_id
      - labels:
          level:
          tenant_id:
      - timestamp:
          source: timestamp
          format: RFC3339Nano
    relabel_configs:
      - source_labels: [__meta_kubernetes_pod_label_app_kubernetes_io_name]
        target_label: app
      - source_labels: [__meta_kubernetes_pod_label_app_kubernetes_io_component]
        target_label: component
      - source_labels: [__meta_kubernetes_namespace]
        target_label: namespace
      - source_labels: [__meta_kubernetes_pod_name]
        target_label: pod
```

### Log Queries in Grafana

```yaml
# Useful LogQL queries for Grafana

# Error logs by service
{app="novasight", component="backend"} |= "ERROR"

# Request logs with latency > 1s
{app="novasight"} | json | duration_ms > 1000

# Logs for specific tenant
{tenant_id="tenant-uuid-here"}

# Failed auth attempts
{app="novasight"} |= "authentication" |= "failed"

# Query execution logs
{app="novasight"} | json | message =~ "Query.*"

# Template validation errors
{app="novasight"} |= "template" |= "validation" |= "error"
```

## Expected Output

```
backend/app/
├── utils/
│   └── logger.py
└── middleware/
    └── request_logging.py

logging/
├── loki/
│   ├── loki-config.yaml
│   └── loki-deployment.yaml
├── promtail/
│   ├── promtail-config.yaml
│   └── promtail-daemonset.yaml
└── grafana/
    └── dashboards/
        └── logs-dashboard.json
```

## Acceptance Criteria

- [ ] All logs in JSON format
- [ ] Request ID in every log
- [ ] Tenant ID in tenant-scoped logs
- [ ] Request/response logged
- [ ] Exceptions logged with stack trace
- [ ] Logs ship to Loki
- [ ] Grafana can query logs
- [ ] Log retention configured
- [ ] Sensitive data not logged

## Reference Documents

- [Infrastructure Agent](../agents/infrastructure-agent.agent.md)
- [Monitoring Setup](./040-monitoring-setup.md)
