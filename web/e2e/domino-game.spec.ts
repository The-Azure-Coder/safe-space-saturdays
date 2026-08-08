import { expect, test } from '@playwright/test'

test.setTimeout(180_000)

test('Dominoes launches, plays a full human and bot turn, and fits mobile', async ({ page }, testInfo) => {
  const email = `domino-e2e-${Date.now()}@example.com`
  const password = 'domino-browser-password-123'

  await page.goto('/registration')
  await page.waitForFunction(() => document.documentElement.dataset.clientReady === 'true', undefined, { timeout: 110_000 })
  await page.getByLabel('Full name').fill('Domino Browser Player')
  await page.getByLabel('Email').fill(email)
  await page.locator('input[name="password"]').fill(password)
  await page.locator('input[name="confirm-password"]').fill(password)
  await page.getByLabel(/I agree to the Safe Space Saturdays/).check()
  await page.getByRole('button', { name: 'Create account' }).click()
  await expect(page).toHaveURL(/\/$/)

  await page.goto('/games')
  const dominoCard = page.locator('.game-tile').filter({ hasText: 'Dominoes' }).first()
  await expect(dominoCard).toBeVisible({ timeout: 110_000 })
  await dominoCard.getByRole('button', { name: 'Play' }).click()
  await expect(page).toHaveURL(/\/games\/session\/[a-f0-9-]+$/)

  const game = page.getByRole('region', { name: 'Domino table' })
  await expect(game).toBeVisible({ timeout: 110_000 })
  await expect(page.getByText('Block Dominoes · 2 players')).toBeVisible()
  await expect(page.locator('.domino-hand-tile')).toHaveCount(7)
  await expect(page.locator('.domino-hand-tile--legal')).toHaveCount(7)
  await page.screenshot({ path: testInfo.outputPath('domino-desktop-empty.png'), fullPage: true })

  await page.locator('.domino-hand-tile--legal').first().click()
  await expect(page.locator('.domino-chain__cell')).not.toHaveCount(0, { timeout: 20_000 })
  await expect.poll(async () => {
    const legal = await page.locator('.domino-hand-tile--legal').count()
    const passEnabled = await page.getByRole('button', { name: 'Pass turn' }).isEnabled()
    return legal > 0 || passEnabled
  }, { timeout: 30_000 }).toBe(true)
  await expect(page.locator('.domino-hand-tile')).toHaveCount(6)
  await page.screenshot({ path: testInfo.outputPath('domino-desktop-played.png'), fullPage: true })

  await page.setViewportSize({ width: 390, height: 844 })
  await expect(game).toBeVisible()
  await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
  await expect(page.locator('.domino-hand')).toBeVisible()
  await page.screenshot({ path: testInfo.outputPath('domino-mobile.png'), fullPage: true })
})
