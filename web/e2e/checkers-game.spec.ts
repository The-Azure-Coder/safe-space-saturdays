import { expect, test } from '@playwright/test'

test.setTimeout(180_000)

test('Checkers is featured, launches with a bot, and stays usable on mobile', async ({ page }) => {
  const email = `checkers-e2e-${Date.now()}@example.com`
  const password = 'checkers-browser-password-123'

  await page.goto('/registration')
  await page.waitForFunction(() => document.documentElement.dataset.clientReady === 'true', undefined, { timeout: 110_000 })
  await page.getByLabel('Full name').fill('Checkers Browser Player')
  await page.getByLabel('Email').fill(email)
  await page.locator('input[name="password"]').fill(password)
  await page.locator('input[name="confirm-password"]').fill(password)
  await page.getByLabel(/I agree to the Safe Space Saturdays/).check()
  await page.getByRole('button', { name: 'Create account' }).click()
  await expect(page).toHaveURL(/\/$/)

  await page.goto('/games')
  const card = page.locator('.game-tile').filter({ hasText: 'Checkers' }).first()
  await expect(card).toBeVisible({ timeout: 110_000 })
  await card.getByRole('button', { name: 'Play' }).click()
  await expect(page).toHaveURL(/\/games\/session\/[a-f0-9-]+$/)

  const game = page.getByRole('region', { name: 'Checkers game' })
  await expect(game).toBeVisible({ timeout: 110_000 })
  await expect(page.getByRole('grid', { name: 'Checkers board' }).getByRole('gridcell')).toHaveCount(64)
  await expect(page.getByText('Captures are required')).toBeVisible()
  await page.setViewportSize({ width: 390, height: 844 })
  await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
})
