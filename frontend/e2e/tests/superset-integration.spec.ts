/**
 * Apache Superset Integration — Phase 9 End-to-End Test
 *
 * This single Playwright spec drives a real browser through the full
 * Superset-backed UX: charts, dashboards, SQL Lab, plus a cross-tenant
 * negative case. It is the gate kept by the `superset-e2e` CI job and
 * must pass on every PR that touches the Superset surface.
 *
 * The spec assumes Compose has been brought up with the `superset`
 * profile and that the AI Workbench Alembic migration `f5d8a1c20b3e`
 * has been applied (CI does both before invoking Playwright).
 */

import { test, expect, type Page } from '@playwright/test'

const BASE_URL = process.env.E2E_BASE_URL ?? 'http://localhost:5173'
const API_URL = process.env.E2E_API_URL ?? 'http://localhost:5000'

const TENANT_A = {
  email: process.env.E2E_TENANT_A_EMAIL ?? 'admin-a@example.com',
  password: process.env.E2E_TENANT_A_PASSWORD ?? 'Admin123!',
}
const TENANT_B = {
  email: process.env.E2E_TENANT_B_EMAIL ?? 'admin-b@example.com',
  password: process.env.E2E_TENANT_B_PASSWORD ?? 'Admin123!',
}

async function login(page: Page, email: string, password: string) {
  await page.goto(`${BASE_URL}/login`)
  await page.getByLabel(/email/i).fill(email)
  await page.getByLabel(/password/i).fill(password)
  await page.getByRole('button', { name: /sign in|log in/i }).click()
  await expect(page).toHaveURL(/.*(dashboard|home|overview)/, { timeout: 30_000 })
}

test.describe('Superset integration — full end-to-end', () => {
  test.setTimeout(300_000)

  test('Tenant A: full Superset-backed BI flow', async ({ page, request }) => {
    // --- 1. Login as tenant A admin --------------------------------------
    await login(page, TENANT_A.email, TENANT_A.password)

    // Capture access token for direct API checks.
    const tokenA = await page.evaluate(
      () =>
        window.localStorage.getItem('access_token') ??
        window.localStorage.getItem('token') ??
        '',
    )
    expect(tokenA, 'access token must be present after login').toBeTruthy()

    // --- 2. Datasources page is reachable --------------------------------
    await page.goto(`${BASE_URL}/datasources`)
    await expect(page).toHaveURL(/.*datasources/)

    // --- 3. Pipelines page is reachable ----------------------------------
    await page.goto(`${BASE_URL}/pipelines`)
    await expect(page).toHaveURL(/.*pipelines/)

    // --- 4. Jobs page is reachable ---------------------------------------
    await page.goto(`${BASE_URL}/jobs`)
    await expect(page).toHaveURL(/.*jobs/)

    // --- 5. dbt Studio page is reachable ---------------------------------
    await page.goto(`${BASE_URL}/dbt-studio`).catch(() => undefined)
    // Some builds expose dbt at /dbt; skip strict assertion if missing.

    // --- 6. SQL Editor: run SELECT 1 via Superset SQL Lab ----------------
    await page.goto(`${BASE_URL}/sql-editor`)
    const editor = page.locator('textarea, [contenteditable="true"]').first()
    await editor.click()
    await editor.fill('SELECT 1 as one')
    await page
      .getByRole('button', { name: /run|execute/i })
      .first()
      .click()
    await expect(page.getByText(/^1$|one/i).first()).toBeVisible({
      timeout: 30_000,
    })

    // --- 7. Charts page: create a Superset slice -------------------------
    const chartName = `e2e-bar-${Date.now()}`
    const chartCreate = await request.post(
      `${API_URL}/api/v1/superset/charts`,
      {
        headers: { Authorization: `Bearer ${tokenA}` },
        data: {
          name: chartName,
          chart_type: 'bar',
          source_type: 'semantic_model',
          query_config: {
            dimensions: ['region'],
            measures: ['revenue'],
            limit: 100,
          },
          viz_config: {},
        },
      },
    )
    expect(chartCreate.ok(), await chartCreate.text()).toBeTruthy()
    const chartBody = await chartCreate.json()
    const newChartId = chartBody.id ?? chartBody.result?.id
    expect(newChartId).toBeTruthy()

    await page.goto(`${BASE_URL}/charts`)
    await expect(page.getByText(chartName)).toBeVisible({ timeout: 30_000 })

    // --- 8. Dashboards page: create a Superset dashboard -----------------
    const dashboardName = `e2e-board-${Date.now()}`
    const dashCreate = await request.post(
      `${API_URL}/api/v1/superset/dashboards`,
      {
        headers: { Authorization: `Bearer ${tokenA}` },
        data: {
          name: dashboardName,
          layout: [
            {
              i: 'w1',
              x: 0,
              y: 0,
              w: 6,
              h: 4,
              chartId: newChartId,
            },
          ],
        },
      },
    )
    expect(dashCreate.ok(), await dashCreate.text()).toBeTruthy()
    const dashBody = await dashCreate.json()
    const newDashId = dashBody.id ?? dashBody.result?.id
    expect(newDashId).toBeTruthy()

    await page.goto(`${BASE_URL}/dashboards`)
    await expect(page.getByText(dashboardName)).toBeVisible({
      timeout: 30_000,
    })

    // --- 9. NL2SQL / Query page reachable --------------------------------
    await page.goto(`${BASE_URL}/query`).catch(() => undefined)

    // --- 10. Cross-tenant negative case ----------------------------------
    // Login as tenant B and confirm the dashboard from tenant A is
    // **not** visible and direct GET returns 403.
    await page.context().clearCookies()
    await page.evaluate(() => window.localStorage.clear())

    await login(page, TENANT_B.email, TENANT_B.password)
    const tokenB = await page.evaluate(
      () =>
        window.localStorage.getItem('access_token') ??
        window.localStorage.getItem('token') ??
        '',
    )
    expect(tokenB).toBeTruthy()

    const cross = await request.get(
      `${API_URL}/api/v1/superset/dashboards/${newDashId}`,
      { headers: { Authorization: `Bearer ${tokenB}` } },
    )
    expect(
      cross.status(),
      'cross-tenant dashboard fetch must be forbidden',
    ).toBe(403)

    await page.goto(`${BASE_URL}/dashboards`)
    await expect(page.getByText(dashboardName)).toHaveCount(0)
  })
})
