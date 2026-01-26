# 044 - Performance Testing

## Metadata

```yaml
prompt_id: "044"
phase: 6
agent: "@testing"
model: "sonnet 4.5"
priority: P1
estimated_effort: "3 days"
dependencies: ["034", "035"]
```

## Objective

Implement performance testing suite for load and stress testing.

## Task Description

Create performance tests using k6 to verify system performance under load.

## Requirements

### k6 Test Scripts

```javascript
// performance/k6/api-load-test.js
import http from 'k6/http'
import { check, sleep, group } from 'k6'
import { Rate, Trend } from 'k6/metrics'

// Custom metrics
const errorRate = new Rate('errors')
const queryLatency = new Trend('query_latency')
const dashboardLatency = new Trend('dashboard_latency')

// Test configuration
export const options = {
  stages: [
    { duration: '2m', target: 50 },   // Ramp up
    { duration: '5m', target: 50 },   // Stay at 50 users
    { duration: '2m', target: 100 },  // Ramp up to 100
    { duration: '5m', target: 100 },  // Stay at 100 users
    { duration: '2m', target: 200 },  // Ramp up to 200
    { duration: '5m', target: 200 },  // Stay at 200 users
    { duration: '2m', target: 0 },    // Ramp down
  ],
  thresholds: {
    http_req_duration: ['p(95)<2000', 'p(99)<5000'],
    errors: ['rate<0.01'],  // Error rate < 1%
    query_latency: ['p(95)<3000'],
    dashboard_latency: ['p(95)<1000'],
  },
}

const BASE_URL = __ENV.API_URL || 'http://localhost:5000'
const TEST_TENANT = __ENV.TENANT_SLUG || 'perf-test'

// Get auth token
export function setup() {
  const loginRes = http.post(`${BASE_URL}/api/v1/auth/login`, JSON.stringify({
    email: __ENV.TEST_USER || 'perf-test@example.com',
    password: __ENV.TEST_PASSWORD || 'TestPassword123!',
  }), {
    headers: { 'Content-Type': 'application/json' },
  })
  
  check(loginRes, {
    'login successful': (r) => r.status === 200,
  })
  
  return {
    token: loginRes.json('data.access_token'),
  }
}

export default function(data) {
  const headers = {
    'Authorization': `Bearer ${data.token}`,
    'Content-Type': 'application/json',
  }
  
  group('Dashboard Operations', () => {
    // List dashboards
    const listRes = http.get(`${BASE_URL}/api/v1/dashboards`, { headers })
    check(listRes, {
      'list dashboards status 200': (r) => r.status === 200,
    })
    errorRate.add(listRes.status !== 200)
    dashboardLatency.add(listRes.timings.duration)
    
    // Get specific dashboard
    if (listRes.status === 200 && listRes.json('data').length > 0) {
      const dashboardId = listRes.json('data.0.id')
      const getRes = http.get(`${BASE_URL}/api/v1/dashboards/${dashboardId}`, { headers })
      check(getRes, {
        'get dashboard status 200': (r) => r.status === 200,
      })
      dashboardLatency.add(getRes.timings.duration)
    }
  })
  
  group('Query Operations', () => {
    // Execute a query
    const queryRes = http.post(`${BASE_URL}/api/v1/query/execute`, JSON.stringify({
      query: 'Show total sales by region',
    }), { headers })
    
    check(queryRes, {
      'query status 200': (r) => r.status === 200,
      'query returns data': (r) => r.json('data') !== null,
    })
    errorRate.add(queryRes.status !== 200)
    queryLatency.add(queryRes.timings.duration)
  })
  
  group('Data Source Operations', () => {
    // List data sources
    const listRes = http.get(`${BASE_URL}/api/v1/datasources`, { headers })
    check(listRes, {
      'list datasources status 200': (r) => r.status === 200,
    })
    errorRate.add(listRes.status !== 200)
    
    // Get schema
    if (listRes.status === 200 && listRes.json('data').length > 0) {
      const dsId = listRes.json('data.0.id')
      const schemaRes = http.get(`${BASE_URL}/api/v1/datasources/${dsId}/schema`, { headers })
      check(schemaRes, {
        'get schema status 200': (r) => r.status === 200,
      })
    }
  })
  
  sleep(1)
}

export function teardown(data) {
  // Cleanup if needed
}
```

### Stress Test

```javascript
// performance/k6/stress-test.js
import http from 'k6/http'
import { check, sleep } from 'k6'
import { Rate } from 'k6/metrics'

const errorRate = new Rate('errors')

export const options = {
  stages: [
    { duration: '2m', target: 100 },
    { duration: '5m', target: 100 },
    { duration: '2m', target: 200 },
    { duration: '5m', target: 200 },
    { duration: '2m', target: 300 },
    { duration: '5m', target: 300 },
    { duration: '2m', target: 400 },
    { duration: '5m', target: 400 },
    { duration: '10m', target: 0 },
  ],
  thresholds: {
    errors: ['rate<0.10'],  // Allow up to 10% errors under stress
    http_req_duration: ['p(95)<10000'],  // 10s at p95 under stress
  },
}

// ... similar structure to load test
```

### Spike Test

```javascript
// performance/k6/spike-test.js
import http from 'k6/http'
import { check, sleep } from 'k6'

export const options = {
  stages: [
    { duration: '10s', target: 100 },   // Normal load
    { duration: '1m', target: 100 },
    { duration: '10s', target: 1000 },  // Spike!
    { duration: '3m', target: 1000 },   // Stay at spike
    { duration: '10s', target: 100 },   // Scale down
    { duration: '3m', target: 100 },    // Recovery period
    { duration: '10s', target: 0 },
  ],
  thresholds: {
    http_req_duration: ['p(99)<15000'],  // 15s at p99 during spike
    http_req_failed: ['rate<0.30'],  // Allow 30% failures during spike
  },
}

// ... test implementation
```

### Soak Test

```javascript
// performance/k6/soak-test.js
import http from 'k6/http'
import { check, sleep } from 'k6'

export const options = {
  stages: [
    { duration: '5m', target: 100 },
    { duration: '4h', target: 100 },  // Extended period
    { duration: '5m', target: 0 },
  ],
  thresholds: {
    http_req_duration: ['p(95)<2000'],
    http_req_failed: ['rate<0.01'],
  },
}

// ... test implementation - focuses on memory leaks, DB connection exhaustion
```

### Database Performance Test

```javascript
// performance/k6/database-test.js
import http from 'k6/http'
import { check, sleep, group } from 'k6'
import { Trend } from 'k6/metrics'

const complexQueryLatency = new Trend('complex_query_latency')
const aggregationLatency = new Trend('aggregation_latency')

export const options = {
  scenarios: {
    simple_queries: {
      executor: 'constant-vus',
      vus: 20,
      duration: '10m',
      exec: 'simpleQueries',
    },
    complex_queries: {
      executor: 'constant-vus',
      vus: 5,
      duration: '10m',
      exec: 'complexQueries',
    },
    aggregations: {
      executor: 'constant-vus',
      vus: 10,
      duration: '10m',
      exec: 'aggregations',
    },
  },
  thresholds: {
    complex_query_latency: ['p(95)<30000'],  // Complex queries < 30s
    aggregation_latency: ['p(95)<10000'],    // Aggregations < 10s
  },
}

export function simpleQueries(data) {
  // Simple single-table queries
  const res = http.post(`${BASE_URL}/api/v1/query/execute`, JSON.stringify({
    query: 'SELECT * FROM orders LIMIT 100',
  }), { headers: data.headers })
  
  check(res, { 'simple query ok': (r) => r.status === 200 })
  sleep(1)
}

export function complexQueries(data) {
  // Multi-table joins
  const res = http.post(`${BASE_URL}/api/v1/query/execute`, JSON.stringify({
    query: `
      SELECT c.name, SUM(o.amount) as total
      FROM customers c
      JOIN orders o ON c.id = o.customer_id
      JOIN products p ON o.product_id = p.id
      WHERE o.created_at > now() - INTERVAL 30 DAY
      GROUP BY c.name
      ORDER BY total DESC
      LIMIT 100
    `,
  }), { headers: data.headers })
  
  check(res, { 'complex query ok': (r) => r.status === 200 })
  complexQueryLatency.add(res.timings.duration)
  sleep(5)
}

export function aggregations(data) {
  // Heavy aggregations
  const res = http.post(`${BASE_URL}/api/v1/query/execute`, JSON.stringify({
    query: `
      SELECT 
        toStartOfMonth(created_at) as month,
        region,
        COUNT(*) as orders,
        SUM(amount) as revenue,
        AVG(amount) as avg_order
      FROM orders
      WHERE created_at > now() - INTERVAL 1 YEAR
      GROUP BY month, region
      ORDER BY month, revenue DESC
    `,
  }), { headers: data.headers })
  
  check(res, { 'aggregation ok': (r) => r.status === 200 })
  aggregationLatency.add(res.timings.duration)
  sleep(3)
}
```

### Performance Test Runner

```yaml
# performance/k6/docker-compose.yml
version: '3.8'

services:
  k6:
    image: grafana/k6:latest
    volumes:
      - ./:/scripts
    environment:
      - K6_OUT=influxdb=http://influxdb:8086/k6
      - API_URL=http://backend:5000
    command: run /scripts/api-load-test.js
    depends_on:
      - influxdb
  
  influxdb:
    image: influxdb:1.8
    ports:
      - "8086:8086"
    environment:
      - INFLUXDB_DB=k6
  
  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    volumes:
      - ./grafana/dashboards:/var/lib/grafana/dashboards
      - ./grafana/provisioning:/etc/grafana/provisioning
    depends_on:
      - influxdb
```

### CI Integration

```yaml
# .github/workflows/performance.yml
name: Performance Tests

on:
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM
  workflow_dispatch:

jobs:
  performance-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Start services
        run: docker compose up -d
      
      - name: Wait for services
        run: sleep 60
      
      - name: Run k6 load test
        uses: grafana/k6-action@v0.3.0
        with:
          filename: performance/k6/api-load-test.js
        env:
          API_URL: http://localhost:5000
      
      - name: Upload results
        uses: actions/upload-artifact@v4
        with:
          name: k6-results
          path: summary.json
```

## Expected Output

```
performance/
├── k6/
│   ├── api-load-test.js
│   ├── stress-test.js
│   ├── spike-test.js
│   ├── soak-test.js
│   ├── database-test.js
│   └── docker-compose.yml
├── grafana/
│   └── dashboards/
│       └── k6-results.json
└── README.md
```

## Acceptance Criteria

- [ ] Load test covers all critical endpoints
- [ ] P95 latency < 2s under normal load
- [ ] System handles 200 concurrent users
- [ ] Error rate < 1% under normal load
- [ ] Database queries perform under load
- [ ] Results stored for trend analysis
- [ ] Grafana dashboard for visualization
- [ ] CI integration for regular testing

## Reference Documents

- [Testing Agent](../agents/testing-agent.agent.md)
- [Monitoring Setup](./040-monitoring-setup.md)
