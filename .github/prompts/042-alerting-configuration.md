# 042 - Alerting Configuration

## Metadata

```yaml
prompt_id: "042"
phase: 6
agent: "@infrastructure"
model: "sonnet 4.5"
priority: P1
estimated_effort: "2 days"
dependencies: ["040", "041"]
```

## Objective

Configure alerting with Alertmanager for incident notification.

## Task Description

Set up alert routing, silencing, and notification channels for operational alerts.

## Requirements

### Alertmanager Configuration

```yaml
# monitoring/alertmanager/alertmanager.yaml
global:
  smtp_smarthost: 'smtp.gmail.com:587'
  smtp_from: 'alerts@novasight.io'
  smtp_auth_username: 'alerts@novasight.io'
  smtp_auth_password_file: '/etc/alertmanager/smtp_password'
  
  slack_api_url_file: '/etc/alertmanager/slack_webhook'
  
  pagerduty_url: 'https://events.pagerduty.com/v2/enqueue'

templates:
  - '/etc/alertmanager/templates/*.tmpl'

route:
  group_by: ['alertname', 'cluster', 'service']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h
  receiver: 'default-receiver'
  routes:
    # Critical alerts go to PagerDuty immediately
    - match:
        severity: critical
      receiver: 'pagerduty-critical'
      group_wait: 10s
      repeat_interval: 1h
    
    # Security alerts get special handling
    - match:
        category: security
      receiver: 'security-team'
      group_wait: 0s
      repeat_interval: 30m
    
    # Database alerts
    - match:
        service: database
      receiver: 'database-team'
    
    # Warning alerts go to Slack
    - match:
        severity: warning
      receiver: 'slack-warnings'
      group_wait: 1m
      repeat_interval: 4h
    
    # Info level - just email
    - match:
        severity: info
      receiver: 'email-notifications'
      group_wait: 5m
      repeat_interval: 24h

receivers:
  - name: 'default-receiver'
    slack_configs:
      - channel: '#novasight-alerts'
        send_resolved: true
        title: '{{ template "slack.title" . }}'
        text: '{{ template "slack.text" . }}'
        actions:
          - type: button
            text: 'View in Grafana'
            url: '{{ (index .Alerts 0).Annotations.grafana_url }}'
          - type: button
            text: 'Silence'
            url: '{{ template "silence.url" . }}'
    
  - name: 'pagerduty-critical'
    pagerduty_configs:
      - service_key_file: '/etc/alertmanager/pagerduty_key'
        severity: critical
        description: '{{ template "pagerduty.description" . }}'
        details:
          firing: '{{ template "pagerduty.firing" . }}'
          service: '{{ (index .Alerts 0).Labels.service }}'
          cluster: '{{ (index .Alerts 0).Labels.cluster }}'
    
  - name: 'security-team'
    pagerduty_configs:
      - service_key_file: '/etc/alertmanager/pagerduty_security_key'
        severity: critical
    slack_configs:
      - channel: '#security-incidents'
        send_resolved: true
    email_configs:
      - to: 'security@novasight.io'
        send_resolved: false
    
  - name: 'database-team'
    slack_configs:
      - channel: '#database-ops'
        send_resolved: true
    email_configs:
      - to: 'database-team@novasight.io'
    
  - name: 'slack-warnings'
    slack_configs:
      - channel: '#novasight-warnings'
        send_resolved: true
        color: '{{ if eq .Status "firing" }}warning{{ else }}good{{ end }}'
    
  - name: 'email-notifications'
    email_configs:
      - to: 'ops@novasight.io'
        send_resolved: true

inhibit_rules:
  # Inhibit warning if critical is firing
  - source_match:
      severity: 'critical'
    target_match:
      severity: 'warning'
    equal: ['alertname', 'cluster', 'service']
  
  # Inhibit pod alerts if node is down
  - source_match:
      alertname: 'NodeDown'
    target_match_re:
      alertname: 'Pod.*'
    equal: ['node']
```

### Alert Templates

```yaml
# monitoring/alertmanager/templates/novasight.tmpl
{{ define "slack.title" }}
[{{ .Status | toUpper }}{{ if eq .Status "firing" }}:{{ .Alerts.Firing | len }}{{ end }}] {{ .GroupLabels.alertname }}
{{ end }}

{{ define "slack.text" }}
{{ range .Alerts }}
*Alert:* {{ .Annotations.summary }}
*Description:* {{ .Annotations.description }}
*Severity:* {{ .Labels.severity }}
*Service:* {{ .Labels.service }}
{{ if .Labels.tenant_id }}*Tenant:* {{ .Labels.tenant_id }}{{ end }}
*Started:* {{ .StartsAt.Format "2006-01-02 15:04:05 UTC" }}
{{ if .EndsAt }}*Resolved:* {{ .EndsAt.Format "2006-01-02 15:04:05 UTC" }}{{ end }}
---
{{ end }}
{{ end }}

{{ define "pagerduty.description" }}
{{ (index .Alerts 0).Annotations.summary }}
{{ end }}

{{ define "pagerduty.firing" }}
{{ range .Alerts }}
- {{ .Annotations.summary }}: {{ .Annotations.description }}
{{ end }}
{{ end }}

{{ define "silence.url" }}
{{ .ExternalURL }}/#/silences/new?filter=%7B
{{ range .CommonLabels.SortedPairs }}{{ .Name }}%3D%22{{ .Value }}%22%2C{{ end }}
%7D
{{ end }}
```

### Additional Alert Rules

```yaml
# monitoring/prometheus/rules/security-alerts.yaml
groups:
  - name: security.rules
    rules:
      - alert: HighFailedLoginRate
        expr: |
          sum(rate(novasight_auth_login_failed_total[5m])) > 10
        for: 5m
        labels:
          severity: warning
          category: security
        annotations:
          summary: High rate of failed login attempts
          description: "{{ $value | humanize }} failed logins per second"

      - alert: SuspiciousAPIActivity
        expr: |
          sum(rate(novasight_http_requests_total{status="403"}[5m])) by (remote_addr) > 50
        for: 2m
        labels:
          severity: critical
          category: security
        annotations:
          summary: Potential attack from {{ $labels.remote_addr }}
          description: "High rate of 403 responses from single IP"

      - alert: AuditLogIntegrityViolation
        expr: |
          novasight_audit_log_integrity_issues > 0
        for: 0s
        labels:
          severity: critical
          category: security
        annotations:
          summary: Audit log integrity violation detected
          description: "Possible tampering detected in audit logs"

---
# monitoring/prometheus/rules/business-alerts.yaml
groups:
  - name: business.rules
    rules:
      - alert: TenantQuotaExceeded
        expr: |
          novasight_tenant_usage_bytes / novasight_tenant_quota_bytes > 0.9
        for: 1h
        labels:
          severity: warning
        annotations:
          summary: Tenant {{ $labels.tenant_id }} approaching quota
          description: "Tenant is at {{ $value | humanizePercentage }} of quota"

      - alert: NoQueriesInHour
        expr: |
          sum(increase(novasight_query_execution_seconds_count[1h])) == 0
        for: 1h
        labels:
          severity: warning
        annotations:
          summary: No queries executed in the last hour
          description: "Possible system issue - no query activity"

      - alert: IngestionPipelineStalled
        expr: |
          sum(rate(novasight_ingestion_records_total[15m])) == 0
        for: 30m
        labels:
          severity: critical
        annotations:
          summary: Data ingestion pipeline stalled
          description: "No records ingested in 30 minutes"
```

### On-Call Schedule Integration

```yaml
# monitoring/alertmanager/oncall-config.yaml
# Example integration with Grafana OnCall or PagerDuty

# PagerDuty schedule reference
pagerduty:
  schedules:
    - name: primary-oncall
      id: SCHEDULE_ID_1
    - name: security-oncall
      id: SCHEDULE_ID_2

# Escalation policies
escalation:
  default:
    - wait: 5m
      notify: primary-oncall
    - wait: 15m
      notify: engineering-manager
    - wait: 30m
      notify: vp-engineering
  
  security:
    - wait: 0s
      notify: security-oncall
    - wait: 5m
      notify: security-lead
    - wait: 15m
      notify: ciso
```

## Expected Output

```
monitoring/alertmanager/
├── alertmanager.yaml
├── templates/
│   ├── novasight.tmpl
│   └── slack.tmpl
├── secrets/
│   └── README.md (instructions for secrets)
└── oncall-config.yaml

monitoring/prometheus/rules/
├── novasight.yaml
├── infrastructure.yaml
├── security-alerts.yaml
└── business-alerts.yaml
```

## Acceptance Criteria

- [ ] Critical alerts page on-call
- [ ] Warnings go to Slack
- [ ] Security alerts have special routing
- [ ] Alerts include runbook links
- [ ] Silencing works correctly
- [ ] Inhibition rules prevent noise
- [ ] Escalation policies work
- [ ] Alert templates are informative

## Reference Documents

- [Infrastructure Agent](../agents/infrastructure-agent.agent.md)
- [Monitoring Setup](./040-monitoring-setup.md)
