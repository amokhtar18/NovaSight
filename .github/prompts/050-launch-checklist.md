# 050 - Launch Checklist

## Metadata

```yaml
prompt_id: "050"
phase: 6
agent: "@orchestrator"
model: "opus 4.5"
priority: P0
estimated_effort: "1 day"
dependencies: ["all previous"]
```

## Objective

Create comprehensive launch checklist ensuring production readiness.

## Task Description

Document all verification steps required before production launch.

## Requirements

### Pre-Launch Checklist

```markdown
<!-- docs/launch/checklist.md -->
# NovaSight Production Launch Checklist

## 1. Security ✅

### Authentication & Authorization
- [ ] JWT secret is production-grade (256+ bits)
- [ ] Password hashing uses Argon2id
- [ ] Password policy enforced (12+ chars, complexity)
- [ ] Session timeout configured (15 min idle)
- [ ] Refresh token rotation enabled
- [ ] CORS configured for production domains only
- [ ] CSRF protection enabled

### Data Security
- [ ] Encryption master key rotated from dev
- [ ] All credentials encrypted at rest
- [ ] TLS 1.3 enforced for all connections
- [ ] Database connections use SSL
- [ ] Secrets stored in vault (not env vars)
- [ ] No hardcoded credentials in code

### Access Control
- [ ] RBAC permissions verified
- [ ] Tenant isolation tested
- [ ] Admin accounts secured with MFA
- [ ] Default accounts disabled/removed
- [ ] Rate limiting enabled on all endpoints
- [ ] API key rotation process documented

### Compliance
- [ ] Security scan passed (no critical/high)
- [ ] Dependency vulnerabilities addressed
- [ ] OWASP Top 10 mitigations in place
- [ ] Privacy policy published
- [ ] Terms of service published
- [ ] Data retention policy implemented

---

## 2. Infrastructure ✅

### Kubernetes Cluster
- [ ] Production cluster provisioned
- [ ] Node autoscaling configured
- [ ] Pod resource limits set
- [ ] Pod disruption budgets defined
- [ ] Network policies applied
- [ ] RBAC for service accounts

### Databases
- [ ] PostgreSQL HA configured
- [ ] ClickHouse replication enabled
- [ ] Redis sentinel/cluster mode
- [ ] Connection pooling configured
- [ ] Max connections appropriate
- [ ] Storage provisioned with headroom

### Networking
- [ ] Load balancer configured
- [ ] SSL certificates installed
- [ ] DNS records created
- [ ] CDN configured for static assets
- [ ] DDoS protection enabled
- [ ] WAF rules configured

### Disaster Recovery
- [ ] Backup schedule configured
- [ ] Backup verification tested
- [ ] Point-in-time recovery tested
- [ ] DR runbook documented
- [ ] Failover tested

---

## 3. Application ✅

### Backend
- [ ] All tests passing
- [ ] No critical code smells
- [ ] Debug mode disabled
- [ ] Error messages sanitized
- [ ] Logging configured (no sensitive data)
- [ ] Health endpoints working
- [ ] Metrics exposed

### Frontend
- [ ] Production build optimized
- [ ] Bundle size acceptable (< 500KB gzipped)
- [ ] No console errors
- [ ] Error boundaries configured
- [ ] Analytics integrated
- [ ] Loading states implemented

### API
- [ ] Rate limiting enabled
- [ ] Request validation working
- [ ] Error responses consistent
- [ ] API documentation updated
- [ ] OpenAPI spec valid
- [ ] Versioning strategy clear

### Template Engine (ADR-002)
- [ ] All templates reviewed
- [ ] Input validation strict
- [ ] SQL injection prevention verified
- [ ] Template whitelist enforced
- [ ] Audit logging for generations

---

## 4. Data Processing ✅

### Airflow
- [ ] DAGs deployed to production
- [ ] Executor configured (Celery/K8s)
- [ ] Resource limits set
- [ ] Failure alerts configured
- [ ] Log retention configured
- [ ] Secrets backend configured

### dbt
- [ ] Production profiles configured
- [ ] Models tested
- [ ] Documentation generated
- [ ] Run schedule configured
- [ ] Failure notifications enabled

### Ollama
- [ ] Model deployed (codellama:13b)
- [ ] GPU resources allocated
- [ ] Rate limiting configured
- [ ] Fallback behavior defined
- [ ] Response caching enabled

---

## 5. Monitoring & Observability ✅

### Metrics
- [ ] Prometheus scraping all services
- [ ] Custom metrics exposed
- [ ] Dashboards created:
  - [ ] System overview
  - [ ] API performance
  - [ ] Database health
  - [ ] Business metrics
- [ ] SLO/SLI defined

### Logging
- [ ] Centralized logging configured
- [ ] Log retention policy set
- [ ] Log queries documented
- [ ] Sensitive data filtered
- [ ] Log levels appropriate

### Alerting
- [ ] Alert rules configured
- [ ] On-call rotation set
- [ ] Escalation policies defined
- [ ] Runbooks linked to alerts
- [ ] Test alerts triggered

### Tracing
- [ ] Distributed tracing enabled
- [ ] Trace sampling configured
- [ ] Cross-service traces working

---

## 6. Performance ✅

### Load Testing
- [ ] Load test completed
- [ ] P95 latency < 2s
- [ ] Throughput meets requirements
- [ ] No memory leaks detected
- [ ] Database queries optimized

### Scaling
- [ ] HPA configured
- [ ] Scaling policies tested
- [ ] Burst capacity available
- [ ] Cost estimates reviewed

### Caching
- [ ] Query cache configured
- [ ] Static asset caching
- [ ] API response caching
- [ ] Cache invalidation tested

---

## 7. Documentation ✅

### User Documentation
- [ ] Getting started guide
- [ ] Feature documentation
- [ ] FAQ/Troubleshooting
- [ ] Video tutorials (optional)

### Technical Documentation
- [ ] API documentation
- [ ] Architecture overview
- [ ] Deployment guide
- [ ] Operations runbook

### Legal
- [ ] Privacy policy
- [ ] Terms of service
- [ ] Cookie policy
- [ ] Data processing agreement

---

## 8. Operational Readiness ✅

### Team Readiness
- [ ] On-call schedule set
- [ ] Escalation contacts listed
- [ ] Runbooks reviewed by team
- [ ] Incident response trained
- [ ] Communication channels ready

### Customer Support
- [ ] Support email configured
- [ ] Support portal ready
- [ ] FAQ published
- [ ] Known issues documented

### Business Continuity
- [ ] Status page configured
- [ ] Maintenance window process
- [ ] Customer notification process
- [ ] SLA commitments documented

---

## Final Sign-Off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Engineering Lead | | | |
| Security Lead | | | |
| Operations Lead | | | |
| Product Owner | | | |
| CTO | | | |

---

## Launch Day Procedure

1. **T-24h**: Final staging verification
2. **T-12h**: Team briefing, confirm on-call
3. **T-1h**: Pre-launch checks
4. **T-0**: Execute deployment
5. **T+1h**: Monitor dashboards
6. **T+4h**: First check-in
7. **T+24h**: Post-launch review

## Rollback Criteria

Rollback immediately if:
- Error rate > 5%
- P95 latency > 10s
- Any data integrity issue
- Security vulnerability discovered
- Customer-impacting bug
```

## Expected Output

```
docs/launch/
├── checklist.md
├── sign-off-template.md
├── launch-day-procedure.md
├── rollback-criteria.md
└── post-launch-review-template.md
```

## Acceptance Criteria

- [ ] All checklist items verifiable
- [ ] Sign-off process defined
- [ ] Launch day procedure clear
- [ ] Rollback criteria documented
- [ ] Post-launch review scheduled
- [ ] Team has reviewed checklist
- [ ] All sections completed
- [ ] Go/No-Go decision clear

## Reference Documents

- [Orchestrator Agent](../agents/novasight-orchestrator.agent.md)
- [All Implementation Prompts](./README.md)
- [Deployment Runbook](./049-deployment-runbook.md)

---

## 🎉 Congratulations!

You have completed all 50 implementation prompts for NovaSight!

### Summary of Phases

| Phase | Prompts | Components |
|-------|---------|------------|
| 1: Foundation | 001-007 | Infrastructure, Database, Auth, React |
| 2: Core Components | 008-016 | Template Engine, Data Sources |
| 3: Semantic & AI | 017-023 | dbt, Semantic Layer, NL-to-SQL |
| 4: Analytics UI | 024-027 | Dashboard, Charts, Query Interface |
| 5: Administration | 028-033 | Admin, RBAC, Audit, Encryption |
| 6: Testing & DevOps | 034-050 | Tests, CI/CD, Monitoring, Docs |

### Next Steps

1. Execute prompts in order
2. Use designated agents for each prompt
3. Follow acceptance criteria
4. Reference ADR-002 for all code generation
5. Complete launch checklist before production
