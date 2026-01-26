# 049 - Deployment Runbook

## Metadata

```yaml
prompt_id: "049"
phase: 6
agent: "@infrastructure"
model: "sonnet 4.5"
priority: P0
estimated_effort: "2 days"
dependencies: ["037", "038", "039", "043"]
```

## Objective

Create comprehensive deployment runbook for production operations.

## Task Description

Document all operational procedures for deploying, scaling, and maintaining NovaSight.

## Requirements

### Deployment Runbook

```markdown
<!-- docs/operations/deployment-runbook.md -->
# NovaSight Deployment Runbook

## Table of Contents
1. [Pre-Deployment Checklist](#pre-deployment-checklist)
2. [Deployment Procedures](#deployment-procedures)
3. [Rollback Procedures](#rollback-procedures)
4. [Scaling Operations](#scaling-operations)
5. [Incident Response](#incident-response)

---

## Pre-Deployment Checklist

### Before Every Deployment

- [ ] All tests passing in CI
- [ ] Code review approved
- [ ] Security scan passed
- [ ] Release notes prepared
- [ ] Database migrations reviewed
- [ ] On-call engineer notified
- [ ] Maintenance window scheduled (if needed)

### For Major Releases

- [ ] Load testing completed
- [ ] Staging environment validated
- [ ] Customer communication prepared
- [ ] Rollback plan documented
- [ ] Feature flags configured
- [ ] Monitoring dashboards ready

---

## Deployment Procedures

### Standard Deployment (Staging)

```bash
# 1. Ensure you're on the correct branch
git checkout develop
git pull origin develop

# 2. Tag the release
git tag -a v1.2.3 -m "Release v1.2.3"
git push origin v1.2.3

# 3. Trigger deployment (automatic via GitHub Actions)
# Monitor: https://github.com/novasight/novasight/actions

# 4. Verify deployment
kubectl get pods -n novasight-staging
curl https://staging.novasight.io/api/v1/health

# 5. Run smoke tests
npm run test:smoke:staging
```

### Production Deployment

```bash
# 1. Merge to main
git checkout main
git merge develop
git push origin main

# 2. Create production tag
git tag -a v1.2.3-prod -m "Production release v1.2.3"
git push origin v1.2.3-prod

# 3. Deploy to production
# Option A: Automatic (via GitHub Actions with approval)
# Option B: Manual
kubectl set image deployment/backend \
  backend=ghcr.io/novasight/backend:v1.2.3 \
  -n novasight-prod

kubectl set image deployment/frontend \
  frontend=ghcr.io/novasight/frontend:v1.2.3 \
  -n novasight-prod

# 4. Watch rollout
kubectl rollout status deployment/backend -n novasight-prod
kubectl rollout status deployment/frontend -n novasight-prod

# 5. Run database migrations
kubectl exec -n novasight-prod deployment/backend -- flask db upgrade

# 6. Verify deployment
curl https://api.novasight.io/api/v1/health
npm run test:smoke:prod

# 7. Monitor for 30 minutes
# Watch: Grafana dashboard
# Check: Error rate, latency, user reports
```

### Database Migration Deployment

```bash
# For migrations with downtime

# 1. Announce maintenance window
./scripts/notify-maintenance.sh --start-time "2024-01-15 02:00 UTC" --duration 30

# 2. Enable maintenance mode
kubectl scale deployment/backend --replicas=0 -n novasight-prod

# 3. Backup database
kubectl exec -n novasight-prod postgresql-0 -- pg_dumpall > backup_$(date +%Y%m%d).sql

# 4. Run migrations
kubectl run migration-job --image=ghcr.io/novasight/backend:v1.2.3 \
  --restart=Never \
  --env="DATABASE_URL=$DATABASE_URL" \
  -- flask db upgrade

# 5. Verify migration
kubectl logs migration-job

# 6. Scale backend up
kubectl scale deployment/backend --replicas=5 -n novasight-prod

# 7. Disable maintenance mode
./scripts/notify-maintenance.sh --end

# 8. Verify functionality
npm run test:smoke:prod
```

---

## Rollback Procedures

### Immediate Rollback (No DB Changes)

```bash
# Rollback to previous deployment
kubectl rollout undo deployment/backend -n novasight-prod
kubectl rollout undo deployment/frontend -n novasight-prod

# Verify rollback
kubectl rollout status deployment/backend -n novasight-prod

# Confirm health
curl https://api.novasight.io/api/v1/health
```

### Rollback with Database Migration

```bash
# 1. Identify target migration
flask db history

# 2. Downgrade database
kubectl exec -n novasight-prod deployment/backend -- flask db downgrade <revision>

# 3. Deploy previous version
kubectl set image deployment/backend \
  backend=ghcr.io/novasight/backend:v1.2.2 \
  -n novasight-prod

# 4. Verify
curl https://api.novasight.io/api/v1/health
```

### Rollback from Backup

```bash
# Last resort - restore from backup

# 1. Stop all pods
kubectl scale deployment/backend --replicas=0 -n novasight-prod

# 2. Restore PostgreSQL
kubectl exec -i postgresql-0 -n novasight-prod -- psql < backup_20240115.sql

# 3. Restore ClickHouse
clickhouse-backup restore backup_20240115

# 4. Deploy known-good version
kubectl set image deployment/backend backend=ghcr.io/novasight/backend:v1.2.0 -n novasight-prod

# 5. Scale up
kubectl scale deployment/backend --replicas=5 -n novasight-prod
```

---

## Scaling Operations

### Horizontal Scaling

```bash
# Manual scaling
kubectl scale deployment/backend --replicas=10 -n novasight-prod

# Enable autoscaling
kubectl autoscale deployment/backend \
  --min=5 --max=20 \
  --cpu-percent=70 \
  -n novasight-prod

# Check HPA status
kubectl get hpa -n novasight-prod
```

### Database Scaling

```bash
# Add ClickHouse replica
helm upgrade novasight ./helm/novasight \
  --set clickhouse.replicaCount=3 \
  -n novasight-prod

# Increase PostgreSQL resources
kubectl patch deployment postgresql \
  -p '{"spec":{"template":{"spec":{"containers":[{"name":"postgresql","resources":{"limits":{"memory":"8Gi"}}}]}}}}' \
  -n novasight-prod
```

### Emergency Capacity

```bash
# Burst capacity for traffic spike
kubectl scale deployment/backend --replicas=30 -n novasight-prod
kubectl scale deployment/frontend --replicas=10 -n novasight-prod

# Add more nodes (if using managed K8s)
az aks scale --resource-group novasight --name novasight-prod --node-count 10
```

---

## Incident Response

### Severity Levels

| Level | Description | Response Time | Examples |
|-------|-------------|---------------|----------|
| SEV1 | Complete outage | 15 min | API down, data loss |
| SEV2 | Major degradation | 30 min | Slow queries, auth issues |
| SEV3 | Minor issue | 4 hours | UI bug, minor feature broken |
| SEV4 | Low impact | 24 hours | Cosmetic issue |

### Incident Procedures

```bash
# 1. Acknowledge incident
# PagerDuty: Acknowledge alert
# Slack: Post in #incidents

# 2. Assess impact
kubectl get pods -n novasight-prod
kubectl logs -f deployment/backend -n novasight-prod --tail=100
# Check Grafana dashboards

# 3. Communicate
./scripts/post-status.sh --status "investigating" --message "API latency increased"

# 4. Mitigate
# Options: restart, scale, rollback, failover

# 5. Resolve
# Fix the root cause or implement workaround

# 6. Post-mortem
# Schedule within 48 hours
# Document: timeline, root cause, action items
```

### Common Issues & Fixes

| Issue | Symptoms | Quick Fix |
|-------|----------|-----------|
| High latency | P95 > 2s | Scale up, check DB |
| 5xx errors | Error rate > 1% | Check logs, restart pods |
| Auth failures | 401 responses | Check JWT secret, Redis |
| DB connection | Connection timeout | Restart DB, check limits |
| Memory pressure | OOMKilled pods | Increase limits, scale up |
```

---

## Emergency Contacts

| Role | Name | Phone | Slack |
|------|------|-------|-------|
| Primary On-Call | Rotating | See PagerDuty | @oncall |
| Backend Lead | John Doe | +1-xxx-xxx-xxxx | @johnd |
| Infrastructure | Jane Smith | +1-xxx-xxx-xxxx | @janes |
| Security | Bob Wilson | +1-xxx-xxx-xxxx | @bobw |
```

## Expected Output

```
docs/operations/
├── deployment-runbook.md
├── scaling-guide.md
├── incident-response.md
├── maintenance-procedures.md
├── disaster-recovery.md
└── checklists/
    ├── pre-deployment.md
    ├── production-release.md
    └── incident-response.md
```

## Acceptance Criteria

- [ ] All procedures documented
- [ ] Commands tested and verified
- [ ] Rollback procedures clear
- [ ] Scaling operations documented
- [ ] Incident response defined
- [ ] Emergency contacts listed
- [ ] Checklists available
- [ ] Runbook reviewed by ops team

## Reference Documents

- [Infrastructure Agent](../agents/infrastructure-agent.agent.md)
- [CI/CD Pipeline](./037-cicd-pipeline.md)
- [Backup Recovery](./043-backup-recovery.md)
