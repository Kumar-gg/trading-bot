import { test, expect } from '@playwright/test'

test.describe('feature', () => {
  test('create bot page lists strategies with categories', async ({ page }) => {
    await page.goto('/bots/new')
    await expect(page.getByRole('heading', { name: 'Create bot' })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Trend' })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Create' })).toBeVisible()
  })

  test('create bot and see it on dashboard', async ({ page }) => {
    const name = `E2E Bot ${Date.now()}`
    await page.goto('/bots/new')
    await page.getByLabel('Name').fill(name)
    await page.getByRole('button', { name: 'Create' }).click()
    await expect(page.getByRole('heading', { name })).toBeVisible()
    await page.goto('/')
    await expect(page.getByText(name)).toBeVisible()
  })

  test('bot detail shows control bar states', async ({ page }) => {
    const name = `Controls ${Date.now()}`
    await page.goto('/bots/new')
    await page.getByLabel('Name').fill(name)
    await page.getByRole('button', { name: 'Create' }).click()
    await expect(page.getByText('Current mode')).toBeVisible()
    await expect(page.getByRole('button', { name: /start/i })).toBeEnabled()
    await page.getByRole('button', { name: /^start$/i }).click()
    await expect(page.locator('.bot-state-step.is-current')).toContainText('Running')
    await expect(page.locator('.bot-control-actions').getByRole('button', { name: /^pause$/i })).toBeEnabled()
  })
})
