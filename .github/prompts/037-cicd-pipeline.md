# 037 - CI/CD Pipeline

## Metadata

```yaml
prompt_id: "037"
phase: 6
agent: "@infrastructure"
model: "sonnet 4.5"
priority: P0
estimated_effort: "3 days"
dependencies: ["001", "034", "035", "036"]
```

## Objective

Implement CI/CD pipeline using GitHub Actions for automated testing and deployment.

## Task Description

Create GitHub Actions workflows for continuous integration and deployment to staging/production.

## Requirements

### CI Workflow

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

env:
  PYTHON_VERSION: '3.11'
  NODE_VERSION: '20'

jobs:
  lint:
    name: Lint
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          cache: 'pip'
      
      - name: Set up Node.js
        uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
          cache: 'npm'
          cache-dependency-path: frontend/package-lock.json
      
      - name: Install Python dependencies
        run: |
          pip install ruff black mypy
          pip install -r backend/requirements.txt
      
      - name: Install Node dependencies
        run: npm ci
        working-directory: frontend
      
      - name: Lint Python
        run: |
          ruff check backend/
          black --check backend/
          mypy backend/app --ignore-missing-imports
      
      - name: Lint TypeScript
        run: npm run lint
        working-directory: frontend
      
      - name: Type check TypeScript
        run: npm run type-check
        working-directory: frontend

  test-backend:
    name: Backend Tests
    runs-on: ubuntu-latest
    needs: lint
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
          POSTGRES_DB: test
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      
      redis:
        image: redis:7
        ports:
          - 6379:6379
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          cache: 'pip'
      
      - name: Install dependencies
        run: |
          pip install -r backend/requirements.txt
          pip install -r backend/requirements-dev.txt
      
      - name: Run unit tests
        env:
          DATABASE_URL: postgresql://test:test@localhost:5432/test
          REDIS_URL: redis://localhost:6379
          SECRET_KEY: test-secret-key
          ENCRYPTION_MASTER_KEY: test-encryption-key
        run: |
          cd backend
          pytest tests/unit --cov=app --cov-report=xml --cov-report=html
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: backend/coverage.xml
          flags: backend

  test-frontend:
    name: Frontend Tests
    runs-on: ubuntu-latest
    needs: lint
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Node.js
        uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
          cache: 'npm'
          cache-dependency-path: frontend/package-lock.json
      
      - name: Install dependencies
        run: npm ci
        working-directory: frontend
      
      - name: Run tests
        run: npm run test -- --coverage
        working-directory: frontend
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: frontend/coverage/lcov.info
          flags: frontend

  integration-tests:
    name: Integration Tests
    runs-on: ubuntu-latest
    needs: [test-backend, test-frontend]
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
      
      - name: Start services
        run: docker compose -f docker-compose.test.yml up -d
      
      - name: Wait for services
        run: |
          sleep 30
          curl --retry 10 --retry-delay 5 http://localhost:5000/api/v1/health
      
      - name: Run integration tests
        run: |
          cd backend
          pytest tests/integration -v
      
      - name: Stop services
        if: always()
        run: docker compose -f docker-compose.test.yml down

  e2e-tests:
    name: E2E Tests
    runs-on: ubuntu-latest
    needs: integration-tests
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Node.js
        uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
      
      - name: Install dependencies
        run: npm ci
        working-directory: frontend
      
      - name: Install Playwright
        run: npx playwright install --with-deps
        working-directory: frontend
      
      - name: Start services
        run: docker compose up -d
      
      - name: Wait for services
        run: |
          sleep 30
          curl --retry 10 --retry-delay 5 http://localhost:5173
      
      - name: Run E2E tests
        run: npx playwright test
        working-directory: frontend
      
      - name: Upload test artifacts
        if: failure()
        uses: actions/upload-artifact@v4
        with:
          name: playwright-report
          path: frontend/playwright-report/

  build:
    name: Build
    runs-on: ubuntu-latest
    needs: e2e-tests
    if: github.event_name == 'push'
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3
      
      - name: Login to Container Registry
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      
      - name: Build and push backend
        uses: docker/build-push-action@v5
        with:
          context: ./backend
          push: true
          tags: |
            ghcr.io/${{ github.repository }}/backend:${{ github.sha }}
            ghcr.io/${{ github.repository }}/backend:latest
          cache-from: type=gha
          cache-to: type=gha,mode=max
      
      - name: Build and push frontend
        uses: docker/build-push-action@v5
        with:
          context: ./frontend
          push: true
          tags: |
            ghcr.io/${{ github.repository }}/frontend:${{ github.sha }}
            ghcr.io/${{ github.repository }}/frontend:latest
```

### Deploy Workflow

```yaml
# .github/workflows/deploy.yml
name: Deploy

on:
  push:
    branches: [main]
  workflow_dispatch:
    inputs:
      environment:
        description: 'Environment to deploy to'
        required: true
        default: 'staging'
        type: choice
        options:
          - staging
          - production

jobs:
  deploy-staging:
    name: Deploy to Staging
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main' || github.event.inputs.environment == 'staging'
    environment: staging
    steps:
      - uses: actions/checkout@v4
      
      - name: Configure kubectl
        uses: azure/k8s-set-context@v3
        with:
          kubeconfig: ${{ secrets.KUBE_CONFIG_STAGING }}
      
      - name: Deploy to Kubernetes
        run: |
          kubectl set image deployment/backend \
            backend=ghcr.io/${{ github.repository }}/backend:${{ github.sha }} \
            -n novasight-staging
          
          kubectl set image deployment/frontend \
            frontend=ghcr.io/${{ github.repository }}/frontend:${{ github.sha }} \
            -n novasight-staging
          
          kubectl rollout status deployment/backend -n novasight-staging
          kubectl rollout status deployment/frontend -n novasight-staging
      
      - name: Run database migrations
        run: |
          kubectl exec -n novasight-staging deployment/backend -- \
            flask db upgrade
      
      - name: Smoke tests
        run: |
          curl --fail https://staging.novasight.io/api/v1/health
          curl --fail https://staging.novasight.io

  deploy-production:
    name: Deploy to Production
    runs-on: ubuntu-latest
    if: github.event.inputs.environment == 'production'
    needs: deploy-staging
    environment: production
    steps:
      - uses: actions/checkout@v4
      
      - name: Configure kubectl
        uses: azure/k8s-set-context@v3
        with:
          kubeconfig: ${{ secrets.KUBE_CONFIG_PRODUCTION }}
      
      - name: Deploy to Kubernetes
        run: |
          kubectl set image deployment/backend \
            backend=ghcr.io/${{ github.repository }}/backend:${{ github.sha }} \
            -n novasight-prod
          
          kubectl set image deployment/frontend \
            frontend=ghcr.io/${{ github.repository }}/frontend:${{ github.sha }} \
            -n novasight-prod
          
          kubectl rollout status deployment/backend -n novasight-prod --timeout=600s
          kubectl rollout status deployment/frontend -n novasight-prod --timeout=600s
      
      - name: Run database migrations
        run: |
          kubectl exec -n novasight-prod deployment/backend -- \
            flask db upgrade
      
      - name: Notify deployment
        uses: slackapi/slack-github-action@v1
        with:
          payload: |
            {
              "text": "NovaSight deployed to production: ${{ github.sha }}"
            }
        env:
          SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK }}
```

### Docker Compose for Testing

```yaml
# docker-compose.test.yml
version: '3.8'

services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_USER: test
      POSTGRES_PASSWORD: test
      POSTGRES_DB: test
    ports:
      - "5432:5432"
    healthcheck:
      test: pg_isready -U test
      interval: 10s
      timeout: 5s
      retries: 5

  clickhouse:
    image: clickhouse/clickhouse-server:23.8
    ports:
      - "8123:8123"
    healthcheck:
      test: wget --spider http://localhost:8123/ping
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  backend:
    build: ./backend
    environment:
      DATABASE_URL: postgresql://test:test@postgres:5432/test
      REDIS_URL: redis://redis:6379
      CLICKHOUSE_HOST: clickhouse
      SECRET_KEY: test-secret-key
    ports:
      - "5000:5000"
    depends_on:
      postgres:
        condition: service_healthy
      clickhouse:
        condition: service_healthy
      redis:
        condition: service_started

  frontend:
    build: ./frontend
    environment:
      VITE_API_URL: http://backend:5000
    ports:
      - "5173:5173"
    depends_on:
      - backend
```

## Expected Output

```
.github/
├── workflows/
│   ├── ci.yml
│   ├── deploy.yml
│   └── security-scan.yml
└── dependabot.yml

docker-compose.test.yml
```

## Acceptance Criteria

- [ ] Lint runs on all PRs
- [ ] Unit tests run in parallel
- [ ] Integration tests use containers
- [ ] E2E tests run against full stack
- [ ] Docker images built and pushed
- [ ] Staging deploys automatically
- [ ] Production requires approval
- [ ] Rollback possible on failure
- [ ] Slack notifications on deploy

## Reference Documents

- [Infrastructure Agent](../agents/infrastructure-agent.agent.md)
- [Unit Test Suite](./034-unit-test-suite.md)
