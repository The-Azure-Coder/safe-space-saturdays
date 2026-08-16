import { expect, test } from '@playwright/test'

test.setTimeout(180_000)

test('ABC Fast or Slow completes timed answers, review, scoring, and rematch flow', async ({ page }) => {
  const email = `abc-e2e-${Date.now()}@example.com`
  const password = 'abc-browser-password-123'

  await page.goto('/registration')
  await page.waitForFunction(() => document.documentElement.dataset.clientReady === 'true', undefined, { timeout: 110_000 })
  await page.getByLabel('Full name').fill('ABC Browser Player')
  await page.getByLabel('Email').fill(email)
  await page.locator('input[name="password"]').fill(password)
  await page.locator('input[name="confirm-password"]').fill(password)
  await page.getByLabel(/I agree to the Safe Space Saturdays/).check()
  await page.getByRole('button', { name: 'Create account' }).click()
  await expect(page).toHaveURL(/\/$/)

  await page.goto('/games')
  const gameCard = page.locator('.game-tile').filter({ hasText: 'ABC Fast or Slow' }).first()
  await expect(gameCard).toBeVisible({ timeout: 110_000 })
  await expect(gameCard.locator('img')).toHaveAttribute('src', /game-abc-fast-slow\.png$/)
  await gameCard.getByRole('button', { name: 'Play' }).click()
  await expect(page).toHaveURL(/\/games\/session\/[a-f0-9-]+$/)

  const game = page.getByRole('region', { name: 'ABC Fast or Slow game' })
  await expect(game).toBeVisible({ timeout: 110_000 })
  await expect(game.getByText(/Dictator \/ letter chooser:/)).toBeVisible()
  await expect(game.getByRole('heading', { name: /Letter [A-Z]/ })).toBeVisible()
  for (let round = 1; round <= 3; round += 1) {
    await game.getByRole('button', { name: 'Submit blank' }).click()
    await expect(game.getByText('Review answers')).toBeVisible({ timeout: 15_000 })
    const validButtons = game.locator('button[aria-label$="valid"]:not([disabled])')
    for (let vote = 0; vote < 8; vote += 1) {
      await expect(validButtons.first()).toBeEnabled()
      await validButtons.first().click()
    }
    if (round < 3) {
      await expect(game.getByRole('button', { name: 'Next round' })).toBeVisible()
      await game.getByRole('button', { name: 'Next round' }).click()
    }
  }
  await expect(game.getByRole('button', { name: 'Play again' })).toBeVisible()
  await expect(game.getByText(/won the word race|A tie|wins!/)).toBeVisible()
  await game.getByRole('button', { name: 'Play again' }).click()
  await expect(game.getByText(/Round 1 of 3/)).toBeVisible()
})
