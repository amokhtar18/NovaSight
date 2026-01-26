# 036 - E2E Test Suite

## Metadata

```yaml
prompt_id: "036"
phase: 6
agent: "@testing"
model: "sonnet 4.5"
priority: P1
estimated_effort: "4 days"
dependencies: ["035"]
```

## Objective

Implement end-to-end tests for critical user journeys using Playwright.

## Task Description

Create Playwright-based E2E tests that verify complete user flows through the UI.

## Requirements

### Playwright Configuration

```typescript
// frontend/playwright.config.ts
import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',
  
  use: {
    baseURL: 'http://localhost:5173',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'on-first-retry',
  },
  
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },
    {
      name: 'Mobile Chrome',
      use: { ...devices['Pixel 5'] },
    },
  ],
  
  webServer: [
    {
      command: 'npm run dev',
      url: 'http://localhost:5173',
      reuseExistingServer: !process.env.CI,
    },
    {
      command: 'cd ../backend && flask run',
      url: 'http://localhost:5000/api/v1/health',
      reuseExistingServer: !process.env.CI,
    },
  ],
})
```

### Test Fixtures

```typescript
// frontend/e2e/fixtures.ts
import { test as base, expect } from '@playwright/test'
import { LoginPage } from './pages/LoginPage'
import { DashboardPage } from './pages/DashboardPage'
import { DataSourcesPage } from './pages/DataSourcesPage'

type Fixtures = {
  loginPage: LoginPage
  dashboardPage: DashboardPage
  dataSourcesPage: DataSourcesPage
  authenticatedPage: void
}

export const test = base.extend<Fixtures>({
  loginPage: async ({ page }, use) => {
    await use(new LoginPage(page))
  },
  
  dashboardPage: async ({ page }, use) => {
    await use(new DashboardPage(page))
  },
  
  dataSourcesPage: async ({ page }, use) => {
    await use(new DataSourcesPage(page))
  },
  
  authenticatedPage: async ({ page, loginPage }, use) => {
    // Login before test
    await loginPage.goto()
    await loginPage.login('test@example.com', 'TestPassword123!')
    await expect(page).toHaveURL(/.*dashboard/)
    await use()
  },
})

export { expect }
```

### Page Objects

```typescript
// frontend/e2e/pages/LoginPage.ts
import { Page, Locator, expect } from '@playwright/test'

export class LoginPage {
  readonly page: Page
  readonly emailInput: Locator
  readonly passwordInput: Locator
  readonly loginButton: Locator
  readonly errorMessage: Locator
  
  constructor(page: Page) {
    this.page = page
    this.emailInput = page.getByLabel('Email')
    this.passwordInput = page.getByLabel('Password')
    this.loginButton = page.getByRole('button', { name: 'Sign In' })
    this.errorMessage = page.getByRole('alert')
  }
  
  async goto() {
    await this.page.goto('/login')
  }
  
  async login(email: string, password: string) {
    await this.emailInput.fill(email)
    await this.passwordInput.fill(password)
    await this.loginButton.click()
  }
  
  async expectError(message: string) {
    await expect(this.errorMessage).toContainText(message)
  }
}

// frontend/e2e/pages/DashboardPage.ts
export class DashboardPage {
  readonly page: Page
  readonly addWidgetButton: Locator
  readonly widgetGrid: Locator
  
  constructor(page: Page) {
    this.page = page
    this.addWidgetButton = page.getByRole('button', { name: 'Add Widget' })
    this.widgetGrid = page.locator('.react-grid-layout')
  }
  
  async goto() {
    await this.page.goto('/dashboards')
  }
  
  async createDashboard(name: string) {
    await this.page.getByRole('button', { name: 'New Dashboard' }).click()
    await this.page.getByLabel('Name').fill(name)
    await this.page.getByRole('button', { name: 'Create' }).click()
  }
  
  async addWidget(type: string, name: string) {
    await this.addWidgetButton.click()
    await this.page.getByRole('option', { name: type }).click()
    await this.page.getByLabel('Widget Name').fill(name)
    await this.page.getByRole('button', { name: 'Add' }).click()
  }
  
  async dragWidget(widgetName: string, targetX: number, targetY: number) {
    const widget = this.page.locator(`[data-widget-name="${widgetName}"]`)
    await widget.dragTo(this.widgetGrid, {
      targetPosition: { x: targetX, y: targetY }
    })
  }
}
```

### Authentication Tests

```typescript
// frontend/e2e/tests/auth.spec.ts
import { test, expect } from '../fixtures'

test.describe('Authentication', () => {
  test('successful login redirects to dashboard', async ({ loginPage, page }) => {
    await loginPage.goto()
    await loginPage.login('test@example.com', 'TestPassword123!')
    
    await expect(page).toHaveURL(/.*dashboard/)
    await expect(page.getByText('Welcome')).toBeVisible()
  })
  
  test('invalid credentials shows error', async ({ loginPage }) => {
    await loginPage.goto()
    await loginPage.login('test@example.com', 'WrongPassword')
    
    await loginPage.expectError('Invalid email or password')
  })
  
  test('logout clears session', async ({ page, loginPage }) => {
    await loginPage.goto()
    await loginPage.login('test@example.com', 'TestPassword123!')
    
    // Click user menu and logout
    await page.getByRole('button', { name: 'User menu' }).click()
    await page.getByRole('menuitem', { name: 'Logout' }).click()
    
    await expect(page).toHaveURL(/.*login/)
    
    // Try to access protected page
    await page.goto('/dashboards')
    await expect(page).toHaveURL(/.*login/)
  })
})
```

### Dashboard Builder Tests

```typescript
// frontend/e2e/tests/dashboard-builder.spec.ts
import { test, expect } from '../fixtures'

test.describe('Dashboard Builder', () => {
  test.beforeEach(async ({ authenticatedPage }) => {
    // Uses fixture to ensure logged in
  })
  
  test('can create a new dashboard', async ({ dashboardPage, page }) => {
    await dashboardPage.goto()
    await dashboardPage.createDashboard('My Test Dashboard')
    
    await expect(page.getByText('My Test Dashboard')).toBeVisible()
    await expect(page.getByText('No widgets yet')).toBeVisible()
  })
  
  test('can add widgets to dashboard', async ({ dashboardPage, page }) => {
    await dashboardPage.goto()
    await dashboardPage.createDashboard('Widget Test')
    
    // Add metric card
    await dashboardPage.addWidget('Metric Card', 'Total Sales')
    await expect(page.locator('[data-widget-name="Total Sales"]')).toBeVisible()
    
    // Add bar chart
    await dashboardPage.addWidget('Bar Chart', 'Sales by Region')
    await expect(page.locator('[data-widget-name="Sales by Region"]')).toBeVisible()
  })
  
  test('can resize and reposition widgets', async ({ dashboardPage, page }) => {
    await dashboardPage.goto()
    await page.getByText('Existing Dashboard').click()
    
    // Enable edit mode
    await page.getByRole('button', { name: 'Edit' }).click()
    
    const widget = page.locator('[data-widget-name="Sales Chart"]')
    const resizeHandle = widget.locator('.react-resizable-handle')
    
    // Resize widget
    await resizeHandle.dragTo(resizeHandle, {
      targetPosition: { x: 100, y: 100 }
    })
    
    // Save
    await page.getByRole('button', { name: 'Save' }).click()
    
    // Refresh and verify
    await page.reload()
    const newWidth = await widget.evaluate(el => el.style.width)
    expect(parseInt(newWidth)).toBeGreaterThan(200)
  })
})
```

### Query Interface Tests

```typescript
// frontend/e2e/tests/query-interface.spec.ts
import { test, expect } from '../fixtures'

test.describe('Query Interface', () => {
  test.beforeEach(async ({ authenticatedPage }) => {})
  
  test('can execute natural language query', async ({ page }) => {
    await page.goto('/query')
    
    // Enter query
    await page.getByRole('textbox').fill(
      'What were the total sales by region last month?'
    )
    
    // Submit
    await page.getByRole('button', { name: 'Ask' }).click()
    
    // Wait for result
    await expect(page.getByText('Results')).toBeVisible({ timeout: 30000 })
    
    // Check chart is displayed
    await expect(page.locator('.recharts-wrapper')).toBeVisible()
    
    // Check can switch to table view
    await page.getByRole('tab', { name: 'Table' }).click()
    await expect(page.getByRole('table')).toBeVisible()
  })
  
  test('can save query result to dashboard', async ({ page }) => {
    await page.goto('/query')
    
    await page.getByRole('textbox').fill('Show revenue trend')
    await page.getByRole('button', { name: 'Ask' }).click()
    
    await expect(page.getByText('Results')).toBeVisible({ timeout: 30000 })
    
    // Save to dashboard
    await page.getByRole('button', { name: 'Save to Dashboard' }).click()
    await page.getByLabel('Dashboard').selectOption('My Dashboard')
    await page.getByLabel('Widget Name').fill('Revenue Trend')
    await page.getByRole('button', { name: 'Save' }).click()
    
    // Verify success
    await expect(page.getByText('Saved to dashboard')).toBeVisible()
  })
})
```

## Expected Output

```
frontend/
├── playwright.config.ts
└── e2e/
    ├── fixtures.ts
    ├── global-setup.ts
    ├── pages/
    │   ├── LoginPage.ts
    │   ├── DashboardPage.ts
    │   ├── DataSourcesPage.ts
    │   └── QueryPage.ts
    └── tests/
        ├── auth.spec.ts
        ├── dashboard-builder.spec.ts
        ├── data-sources.spec.ts
        ├── query-interface.spec.ts
        └── admin.spec.ts
```

## Acceptance Criteria

- [ ] Tests run on Chromium, Firefox, WebKit
- [ ] Mobile viewport tests included
- [ ] Page object pattern used
- [ ] Screenshots captured on failure
- [ ] Traces available for debugging
- [ ] Tests run in < 10 minutes
- [ ] Works in CI/CD pipeline
- [ ] No flaky tests

## Reference Documents

- [Testing Agent](../agents/testing-agent.agent.md)
- [Integration Test Suite](./035-integration-test-suite.md)
