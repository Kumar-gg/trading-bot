import { test, expect } from '@playwright/test'

test.describe('smoke', () => {
  test('dashboard loads and shows navigation', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible({ timeout: 15_000 })
    await expect(page.getByRole('main').getByRole('link', { name: 'New bot' })).toBeVisible()
    await expect(page.getByRole('navigation').getByRole('link', { name: 'Compare' })).toBeVisible()
  })

  test('strategies API reachable through UI proxy', async ({ request }) => {
    const res = await request.get('http://127.0.0.1:5173/api/strategies')
    expect(res.ok()).toBeTruthy()
    const data = await res.json()
    expect(data.length).toBeGreaterThanOrEqual(7)
  })
})
