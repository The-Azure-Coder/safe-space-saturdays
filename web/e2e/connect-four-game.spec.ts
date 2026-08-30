import { expect, test } from '@playwright/test'

test.setTimeout(180_000)

test('Connect Four launches, animates a full turn, and fits mobile', async ({ page }, testInfo) => {
  const email = `connect-four-e2e-${Date.now()}@example.com`
  const password = 'connect-four-browser-password-123'

  await page.goto('/registration')
  await page.waitForFunction(() => document.documentElement.dataset.clientReady === 'true', undefined, { timeout: 110_000 })
  await page.getByLabel('Full name').fill('Connect Four Browser Player')
  await page.getByLabel('Email').fill(email)
  await page.locator('input[name="password"]').fill(password)
  await page.locator('input[name="confirm-password"]').fill(password)
  await page.getByLabel(/I agree to the Safe Space Saturdays/).check()
  await page.getByRole('button', { name: 'Create account' }).click()
  await expect(page).toHaveURL(/\/$/)

  await page.goto('/games')
  const gameCard = page.locator('.game-tile').filter({ hasText: 'Connect Four' }).first()
  await expect(gameCard).toBeVisible({ timeout: 110_000 })
  await gameCard.getByRole('button', { name: 'Play' }).click()
  await expect(page).toHaveURL(/\/games\/play\/[a-f0-9-]+$/)

  const game = page.getByRole('region', { name: 'Connect Four game' })
  const board = page.getByRole('grid', { name: 'Six row by seven column Connect Four board' })
  await expect(game).toBeVisible({ timeout: 110_000 })
  await expect(game.getByText('Game level 1 · Win streak 0')).toBeVisible()
  await expect(board.getByRole('gridcell')).toHaveCount(42)
  await expect(page.getByRole('button', { name: 'Drop coral disc in column 4' })).toBeEnabled()
  await page.screenshot({ path: testInfo.outputPath('connect-four-desktop-empty.png'), fullPage: true })

  await page.getByRole('button', { name: 'Drop coral disc in column 4' }).click()
  await expect.poll(() => page.locator('.connect-four-cell--1').count(), { timeout: 15_000 }).toBe(1)
  await expect.poll(() => page.locator('.connect-four-cell--2').count(), { timeout: 15_000 }).toBe(1)
  await expect(page.getByText('Your turn — choose a column.')).toBeVisible()
  await page.screenshot({ path: testInfo.outputPath('connect-four-desktop-played.png'), fullPage: true })

  await page.setViewportSize({ width: 390, height: 844 })
  await expect(board).toBeVisible()
  await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
  await expect(page.getByRole('button', { name: 'Drop coral disc in column 1' })).toBeVisible()
  await page.screenshot({ path: testInfo.outputPath('connect-four-mobile.png'), fullPage: true })
})
