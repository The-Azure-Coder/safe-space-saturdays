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
  await expect(page.getByRole('button', { name: 'Roll dice' })).toBeEnabled()
  await expect(page.getByText('Maya Bot', { exact: true })).toBeVisible()
  await page.screenshot({ path: testInfo.outputPath('ludo-desktop.png'), fullPage: true })

  let movedToken = false
  for (let attempt = 0; attempt < 30 && !movedToken; attempt += 1) {
    const rollButton = page.locator('.ludo-roll-button')
    await expect(rollButton).toBeEnabled({ timeout: 12_000 })
    await rollButton.click()

    await expect.poll(async () => {
      if (await page.locator('.ludo-token--legal').count()) return 'move'
      return await rollButton.isEnabled() ? 'roll' : 'waiting'
    }, { timeout: 12_000 }).toMatch(/move|roll/)

    const legalToken = page.locator('.ludo-token--legal').first()
    if (await legalToken.count()) {
      const before = await legalToken.getAttribute('aria-label')
      expect(before).not.toBeNull()
      await legalToken.click()
      await expect.poll(async () => page.locator('.ludo-token--red').evaluateAll((tokens) => tokens.map((token) => token.getAttribute('aria-label'))), { timeout: 12_000 }).not.toContain(before)
      movedToken = true
    }
  }
  expect(movedToken, 'A six should eventually expose a legal token and allow a move').toBe(true)

  await page.setViewportSize({ width: 390, height: 844 })
  await expect(board).toBeVisible()
  await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
  await expect(page.locator('.ludo-action-dock')).toBeVisible()
  await page.screenshot({ path: testInfo.outputPath('ludo-mobile.png'), fullPage: true })
})
