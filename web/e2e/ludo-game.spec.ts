import { expect, test } from '@playwright/test'

test.setTimeout(180_000)

test('Ludo launches, rolls, moves a legal token, and fits mobile screens', async ({ page }, testInfo) => {
  const email = `ludo-e2e-${Date.now()}@example.com`
  const password = 'ludo-browser-password-123'

  await page.goto('/registration')
  await page.waitForFunction(() => document.documentElement.dataset.clientReady === 'true', undefined, { timeout: 110_000 })
  await page.getByLabel('Full name').fill('Ludo Browser Player')
  await page.getByLabel('Email').fill(email)
  await page.locator('input[name="password"]').fill(password)
  await page.locator('input[name="confirm-password"]').fill(password)
  await page.getByLabel(/I agree to the Safe Space Saturdays/).check()
  await page.getByRole('button', { name: 'Create account' }).click()
  await expect(page).toHaveURL(/\/$/)

  await page.goto('/games')
  const ludoCard = page.locator('.game-tile').filter({ hasText: 'Ludo' }).first()
  await expect(ludoCard).toBeVisible({ timeout: 110_000 })
  await ludoCard.getByRole('button', { name: 'Play' }).click()
  await expect(page).toHaveURL(/\/games\/session\/[a-f0-9-]+$/)

  const board = page.getByRole('grid', { name: 'Classic fifteen by fifteen Ludo board' })
  await expect(board).toBeVisible()
  await expect(board.getByRole('gridcell')).toHaveCount(52)
  await expect(page.locator('.ludo-die--tap')).toBeEnabled()
  await expect(page.getByLabel('Maya Bot yard')).toContainText('Maya Bot')
  await page.screenshot({ path: testInfo.outputPath('ludo-desktop.png'), fullPage: true })

  const rollButton = page.locator('.ludo-die--tap')
  await rollButton.click()
  await expect(board).toBeVisible()

  await page.setViewportSize({ width: 390, height: 844 })
  await expect(board).toBeVisible()
  await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
  await expect(page.getByRole('region', { name: /Ludo game/ })).toBeVisible()
  await page.screenshot({ path: testInfo.outputPath('ludo-mobile.png'), fullPage: true })
})
