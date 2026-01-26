# 045 - Security Testing

## Metadata

```yaml
prompt_id: "045"
phase: 6
agent: "@security"
model: "opus 4.5"
priority: P0
estimated_effort: "3 days"
dependencies: ["031", "032", "033"]
```

## Objective

Implement security testing suite for vulnerability detection.

## Task Description

Create automated security tests including SAST, DAST, and dependency scanning.

## Requirements

### SAST Configuration (Bandit)

```yaml
# .bandit
[bandit]
exclude_dirs = tests,venv,migrations
skips = B101,B601

# Custom plugin paths
# plugin_path = /path/to/custom/plugins

# Severity level
severity = medium
confidence = medium
```

```yaml
# .github/workflows/security-scan.yml
name: Security Scan

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]
  schedule:
    - cron: '0 4 * * *'  # Daily at 4 AM

jobs:
  sast:
    name: Static Analysis
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Run Bandit
        run: |
          pip install bandit
          bandit -r backend/app -f json -o bandit-report.json || true
      
      - name: Run Semgrep
        uses: returntocorp/semgrep-action@v1
        with:
          config: >-
            p/security-audit
            p/python
            p/flask
            p/owasp-top-ten
          auditOn: push
      
      - name: Upload SAST results
        uses: github/codeql-action/upload-sarif@v2
        with:
          sarif_file: semgrep.sarif
  
  dependency-scan:
    name: Dependency Scan
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Run Trivy vulnerability scanner
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          scan-ref: '.'
          severity: 'CRITICAL,HIGH'
          format: 'sarif'
          output: 'trivy-results.sarif'
      
      - name: Run pip-audit
        run: |
          pip install pip-audit
          pip-audit -r backend/requirements.txt --format json > pip-audit.json || true
      
      - name: Run npm audit
        run: |
          cd frontend
          npm audit --json > npm-audit.json || true
  
  secret-scan:
    name: Secret Scan
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      
      - name: Run Gitleaks
        uses: gitleaks/gitleaks-action@v2
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
      
      - name: Run TruffleHog
        uses: trufflesecurity/trufflehog@main
        with:
          path: ./
          base: main
          extra_args: --only-verified
  
  container-scan:
    name: Container Scan
    runs-on: ubuntu-latest
    needs: [sast]
    steps:
      - uses: actions/checkout@v4
      
      - name: Build backend image
        run: docker build -t novasight-backend:test ./backend
      
      - name: Run Trivy container scan
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: 'novasight-backend:test'
          format: 'sarif'
          output: 'trivy-container.sarif'
          severity: 'CRITICAL,HIGH'
```

### DAST Configuration (ZAP)

```yaml
# security/zap/zap-config.yaml
env:
  contexts:
    - name: "NovaSight API"
      urls:
        - "http://localhost:5000"
      includePaths:
        - "http://localhost:5000/api/.*"
      excludePaths:
        - "http://localhost:5000/api/v1/health"
      authentication:
        method: "json"
        parameters:
          loginPageUrl: "http://localhost:5000/api/v1/auth/login"
          loginRequestData: '{"email":"test@example.com","password":"TestPassword123!"}'
          tokenExtractPattern: '"access_token":"([^"]+)"'
        verification:
          method: "response"
          loggedInIndicator: "user_id"
          loggedOutIndicator: "Invalid token"
      sessionManagement:
        method: "headers"
        parameters:
          headerName: "Authorization"
          headerValue: "Bearer {%token%}"

jobs:
  - type: spider
    parameters:
      maxDuration: 5
      maxChildren: 10
  
  - type: spiderAjax
    parameters:
      maxDuration: 5
  
  - type: passiveScan-config
    parameters:
      maxAlertsPerRule: 10
  
  - type: activeScan
    parameters:
      maxScanDurationInMins: 30
      policy: "API-Scan"
  
  - type: report
    parameters:
      template: "traditional-html"
      reportDir: "/zap/reports"
      reportFile: "zap-report.html"
```

### Security Test Suite

```python
# backend/tests/security/test_authentication.py
import pytest
from app import create_app

class TestAuthenticationSecurity:
    """Security tests for authentication."""
    
    def test_password_hash_not_exposed(self, client, test_user):
        """Ensure password hash is never exposed in API responses."""
        response = client.get(f'/api/v1/users/{test_user.id}', headers=auth_headers)
        data = response.json
        
        assert 'password' not in str(data)
        assert 'password_hash' not in str(data)
        assert 'hash' not in str(data).lower()
    
    def test_rate_limiting_on_login(self, client):
        """Test rate limiting prevents brute force attacks."""
        # Attempt 20 failed logins
        for i in range(20):
            client.post('/api/v1/auth/login', json={
                'email': 'test@example.com',
                'password': f'wrong_password_{i}'
            })
        
        # Next attempt should be rate limited
        response = client.post('/api/v1/auth/login', json={
            'email': 'test@example.com',
            'password': 'any_password'
        })
        
        assert response.status_code == 429
    
    def test_jwt_token_expiration(self, client, test_user, app):
        """Test JWT tokens expire correctly."""
        import time
        from flask_jwt_extended import create_access_token
        
        with app.app_context():
            # Create token with 1 second expiry
            token = create_access_token(
                identity=str(test_user.id),
                expires_delta=timedelta(seconds=1)
            )
        
        # Wait for expiration
        time.sleep(2)
        
        response = client.get('/api/v1/auth/me', headers={
            'Authorization': f'Bearer {token}'
        })
        
        assert response.status_code == 401
    
    def test_session_fixation_prevention(self, client, test_user):
        """Test session IDs change after login."""
        # Login
        response1 = client.post('/api/v1/auth/login', json={
            'email': test_user.email,
            'password': 'TestPassword123!'
        })
        token1 = response1.json['data']['access_token']
        
        # Logout and login again
        client.post('/api/v1/auth/logout', headers={
            'Authorization': f'Bearer {token1}'
        })
        
        response2 = client.post('/api/v1/auth/login', json={
            'email': test_user.email,
            'password': 'TestPassword123!'
        })
        token2 = response2.json['data']['access_token']
        
        # Tokens should be different
        assert token1 != token2


class TestSQLInjection:
    """SQL injection prevention tests."""
    
    INJECTION_PAYLOADS = [
        "'; DROP TABLE users; --",
        "1' OR '1'='1",
        "1; DELETE FROM tenants WHERE 1=1; --",
        "' UNION SELECT * FROM users --",
        "admin'--",
        "1' AND SLEEP(5) --",
    ]
    
    @pytest.mark.parametrize("payload", INJECTION_PAYLOADS)
    def test_query_endpoint_injection(self, client, auth_headers, payload):
        """Test NL-to-SQL endpoint blocks SQL injection."""
        response = client.post('/api/v1/query/execute', json={
            'query': payload
        }, headers=auth_headers)
        
        # Should either reject or sanitize, not execute
        assert response.status_code != 500
        # Should not return data from injection
        assert 'password' not in str(response.json)
    
    @pytest.mark.parametrize("payload", INJECTION_PAYLOADS)
    def test_search_endpoint_injection(self, client, auth_headers, payload):
        """Test search endpoints handle injection attempts."""
        response = client.get(
            f'/api/v1/dashboards?search={payload}',
            headers=auth_headers
        )
        
        assert response.status_code in [200, 400]  # OK or bad request, not error


class TestXSS:
    """XSS prevention tests."""
    
    XSS_PAYLOADS = [
        "<script>alert('XSS')</script>",
        "<img src=x onerror=alert('XSS')>",
        "javascript:alert('XSS')",
        "<svg onload=alert('XSS')>",
        "'-alert('XSS')-'",
    ]
    
    @pytest.mark.parametrize("payload", XSS_PAYLOADS)
    def test_dashboard_name_xss(self, client, auth_headers, payload):
        """Test dashboard creation sanitizes XSS in name."""
        response = client.post('/api/v1/dashboards', json={
            'name': payload,
            'description': 'Test dashboard'
        }, headers=auth_headers)
        
        if response.status_code == 201:
            # If created, verify output is escaped
            assert '<script>' not in response.json['data']['name']
            assert 'javascript:' not in response.json['data']['name']


class TestTenantIsolation:
    """Multi-tenant security isolation tests."""
    
    def test_cross_tenant_data_access(
        self, client, test_user, other_tenant_user
    ):
        """Verify users cannot access other tenant's data."""
        # Login as user from tenant A
        login_a = client.post('/api/v1/auth/login', json={
            'email': test_user.email,
            'password': 'TestPassword123!'
        })
        token_a = login_a.json['data']['access_token']
        
        # Create dashboard as tenant A
        create_resp = client.post('/api/v1/dashboards', json={
            'name': 'Tenant A Dashboard'
        }, headers={'Authorization': f'Bearer {token_a}'})
        dashboard_id = create_resp.json['data']['id']
        
        # Login as user from tenant B
        login_b = client.post('/api/v1/auth/login', json={
            'email': other_tenant_user.email,
            'password': 'TestPassword123!'
        })
        token_b = login_b.json['data']['access_token']
        
        # Try to access tenant A's dashboard from tenant B
        access_resp = client.get(
            f'/api/v1/dashboards/{dashboard_id}',
            headers={'Authorization': f'Bearer {token_b}'}
        )
        
        # Should be forbidden
        assert access_resp.status_code in [403, 404]
```

### Security Scanning Script

```bash
#!/bin/bash
# security/run-security-scan.sh

set -e

echo "=== Running Security Scans ==="

# 1. Static Analysis
echo "Running Bandit (Python SAST)..."
bandit -r backend/app -f html -o reports/bandit.html || true

echo "Running Semgrep..."
semgrep --config auto backend/app --sarif -o reports/semgrep.sarif || true

# 2. Dependency Scanning
echo "Running pip-audit..."
pip-audit -r backend/requirements.txt --format json > reports/pip-audit.json || true

echo "Running npm audit..."
cd frontend && npm audit --json > ../reports/npm-audit.json || true
cd ..

# 3. Container Scanning
echo "Building container..."
docker build -t novasight-backend:scan ./backend

echo "Running Trivy..."
trivy image novasight-backend:scan --format sarif -o reports/trivy.sarif || true

# 4. Secret Scanning
echo "Running Gitleaks..."
gitleaks detect --source . --report-path reports/gitleaks.json --report-format json || true

# 5. DAST (if services are running)
if curl -s http://localhost:5000/api/v1/health > /dev/null; then
  echo "Running ZAP DAST..."
  docker run -v $(pwd):/zap/wrk:rw -t owasp/zap2docker-stable \
    zap.sh -cmd -autorun /zap/wrk/security/zap/zap-config.yaml
fi

echo "=== Scan Complete ==="
echo "Reports available in ./reports/"
```

## Expected Output

```
security/
├── zap/
│   └── zap-config.yaml
├── run-security-scan.sh
└── reports/
    └── .gitkeep

backend/tests/security/
├── __init__.py
├── conftest.py
├── test_authentication.py
├── test_injection.py
├── test_xss.py
├── test_tenant_isolation.py
└── test_template_security.py

.github/workflows/
└── security-scan.yml
```

## Acceptance Criteria

- [ ] SAST runs on every PR
- [ ] Dependency scanning detects vulnerabilities
- [ ] Secret scanning prevents credential leaks
- [ ] Container images scanned
- [ ] DAST runs in staging
- [ ] SQL injection tests pass
- [ ] XSS tests pass
- [ ] Tenant isolation verified
- [ ] Security report generated

## Reference Documents

- [Security Agent](../agents/security-agent.agent.md)
- [RBAC Implementation](./031-rbac-implementation.md)
