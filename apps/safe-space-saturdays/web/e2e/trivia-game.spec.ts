import { expect, test } from '@playwright/test'

test.setTimeout(180_000)

test('Trivia answers, reveals, advances, toggles sound, and fits mobile', async ({ page }, testInfo) => {
  const email = `trivia-e2e-${Date.now()}@example.com`
  const password = 'trivia-browser-password-123'

  await page.goto('/registration')
  await page.waitForFunction(() => document.documentElement.dataset.clientReady === 'true', undefined, { timeout: 110_000 })
  await page.getByLabel('Full name').fill('Trivia Browser Player')
  await page.getByLabel('Email').fill(email)
  await page.locator('input[name="password"]').fill(password)
  await page.locator('input[name="confirm-password"]').fill(password)
  await page.getByLabel(/I agree to the Safe Space Saturdays/).check()
  await page.getByRole('button', { name: 'Create account' }).click()
  await expect(page).toHaveURL(/\/$/)

  await page.goto('/games')
  const gameCard = page.locator('.game-tile').filter({ hasText: 'Trivia' }).first()
  await expect(gameCard).toBeVisible({ timeout: 110_000 })
  await gameCard.getByRole('button', { name: 'Play' }).click()
  await expect(page).toHaveURL(/\/games\/session\/[a-f0-9-]+$/)

  const game = page.getByRole('region', { name: 'Trivia arena' })
  await expect(game).toBeVisible({ timeout: 110_000 })
  await expect(page.locator('.trivia-option')).toHaveCount(4)
  await page.getByRole('button', { name: 'Turn on game sounds' }).click()
  await expect(page.getByRole('button', { name: 'Mute game sounds' })).toHaveAttribute('aria-pressed', 'true')
  await page.screenshot({ path: testInfo.outputPath('trivia-desktop-question.png'), fullPage: true })

  const firstQuestion = await page.locator('.trivia-question h2').innerText()
  await page.locator('.trivia-option').first().click()
  await expect(page.locator('.trivia-option--correct')).toHaveCount(1, { timeout: 15_000 })
  await expect(page.getByRole('button', { name: 'Next question' })).toBeVisible()
  await page.screenshot({ path: testInfo.outputPath('trivia-desktop-reveal.png'), fullPage: true })
  await page.getByRole('button', { name: 'Next question' }).click()
  await expect(page.locator('.trivia-question h2')).not.toHaveText(firstQuestion)
  await expect(page.getByText('Question 2 of 5')).toBeVisible()

  await page.setViewportSize({ width: 390, height: 844 })
  await expect(game).toBeVisible()
  await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
  await expect(page.locator('.trivia-option')).toHaveCount(4)
  await page.screenshot({ path: testInfo.outputPath('trivia-mobile.png'), fullPage: true })
})
