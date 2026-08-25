import { expect, test } from '@playwright/test'

test.setTimeout(300_000)

test('ABC Fast or Slow completes timed answers, reconnects, reviews, scores, and rematches', async ({ page, context }) => {
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
  await expect(gameCard.locator('img')).toHaveAttribute('src', /optimized\/game-abc-fast-slow\.webp$/)
  await gameCard.getByRole('button', { name: 'Play' }).click()
  await expect(page).toHaveURL(/\/games\/session\/[a-f0-9-]+$/)

  const game = page.getByRole('region', { name: 'ABC Fast or Slow game' })
  await expect(game).toBeVisible({ timeout: 110_000 })
  await expect(game.getByText(/Dictator \/ letter chooser:/)).toBeVisible()
  await context.setOffline(true)
  await expect(page.getByRole('status').filter({ hasText: /reconnecting/i })).toBeVisible()
  await context.setOffline(false)
  await expect(page.getByRole('status').filter({ hasText: /reconnecting/i })).toBeHidden({ timeout: 20_000 })
  await expect(game).toBeVisible()
  const chooseLetter = async (speed: 'fast' | 'slow') => {
    const picker = game.locator('.abc-game__picker')
    await expect.poll(async () => (await picker.getByRole('button', { name: new RegExp(`Start ${speed} letter picker`) }).count()) || (await game.getByRole('heading', { name: /Letter [A-Z]/ }).count()) ? 'ready' : 'waiting', { timeout: 30_000 }).toBe('ready')
    if (await picker.getByRole('button', { name: new RegExp(`Start ${speed} letter picker`) }).count()) {
      await picker.getByRole('button', { name: speed === 'slow' ? 'Slow' : 'Fast', exact: true }).click()
      await picker.getByRole('button', { name: `Start ${speed} letter picker` }).click()
      await expect(picker.getByRole('button', { name: 'Stop on this letter' })).toBeVisible()
      await picker.getByRole('button', { name: 'Stop on this letter' }).click()
    }
    await expect(game.getByRole('heading', { name: /Letter [A-Z]/ })).toBeVisible()
  }
  await chooseLetter('slow')
  for (let round = 1; round <= 3; round += 1) {
    const submitBlank = game.getByRole('button', { name: 'Submit blank' })
    if (await submitBlank.isVisible()) await submitBlank.click()
    const validButtons = game.locator('button[aria-label$="valid"]:not([disabled])')
    const nextRound = game.getByRole('button', { name: 'Next round' })
    const playAgain = game.getByRole('button', { name: 'Play again' })
    await expect.poll(async () => {
      if (await validButtons.count()) return 'review'
      if (await nextRound.count()) return 'next'
      if (await playAgain.count()) return 'complete'
      return 'waiting'
    }, { timeout: 70_000 }).toMatch(/review|next|complete/)
    while (await validButtons.count()) await validButtons.first().click()
    if (round < 3) {
      await expect(game.getByRole('button', { name: 'Next round' })).toBeVisible({ timeout: 30_000 })
      await game.getByRole('button', { name: 'Next round' }).click()
      await chooseLetter('fast')
    }
  }
  await expect(game.getByRole('button', { name: 'Play again' })).toBeVisible()
  await expect(game.getByText(/won the word race|A tie|wins!/)).toBeVisible()
  await game.getByRole('button', { name: 'Play again' }).click()
  await expect(game.getByText(/Round 1 of 3/)).toBeVisible()
})
