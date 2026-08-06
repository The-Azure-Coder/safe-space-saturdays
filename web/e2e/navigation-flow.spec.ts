import { expect, test } from '@playwright/test'

test('primary navigation changes screens without a document reload', async ({ page }) => {
  let documentNavigations = 0
  page.on('request', (request) => {
    if (request.isNavigationRequest() && request.frame() === page.mainFrame()) documentNavigations += 1
  })

  await page.goto('/', { waitUntil: 'networkidle' })
  await expect(page.getByRole('link', { name: 'Daily Check-In', exact: true })).toBeVisible({ timeout: 110_000 })
  await page.waitForTimeout(800)

  const routes = [
    ['Daily Check-In', '/check-in'],
    ['Games', '/games'],
    ['Leaderboard', '/leaderboard'],
    ['Community', '/community'],
    ['Quotes', '/quotes'],
    ['Home', '/'],
  ] as const

  for (const [label, route] of routes) {
    const before = documentNavigations
    await page.getByRole('link', { name: label, exact: true }).click()
    await expect(page).toHaveURL(new RegExp(`${route.replace('/', '\\/')}$`))
    expect(documentNavigations, `${label} triggered a full document navigation`).toBe(before)
    await expect(page.getByRole('link', { name: label, exact: true })).toBeVisible({ timeout: 110_000 })
    await page.waitForTimeout(300)
  }
})

test('check-in sliders update their values', async ({ page }) => {
  await page.goto('/check-in', { waitUntil: 'networkidle' })

  const slider = page.getByRole('slider', { name: 'Energy Level' })
  await expect(slider).toBeVisible({ timeout: 110_000 })
  await slider.fill('5')
  await expect(page.locator('output[for="range-energy-level"]')).toHaveText('5 / 5')
})

test('homepage welcome carousel can be navigated without hiding its controls', async ({ page }) => {
  await page.goto('/', { waitUntil: 'networkidle' })
  const carousel = page.locator('[aria-label="A little encouragement"]')
  await expect(carousel).toBeVisible({ timeout: 110_000 })
  const title = carousel.locator('h2')
  const initialTitle = await title.textContent()
  await carousel.getByRole('button', { name: 'Next encouragement' }).click()
  await expect(title).not.toHaveText(initialTitle ?? '')
  await expect(carousel.getByRole('button', { name: 'Previous encouragement' })).toBeVisible()
  await expect(carousel.getByRole('button', { name: 'Next encouragement' })).toBeVisible()
  await expect(carousel.getByRole('button', { name: 'Show encouragement 1' })).toBeVisible()
})

test('homepage welcome carousel auto-advances', async ({ page }) => {
  await page.goto('/', { waitUntil: 'networkidle' })
  const carousel = page.locator('[aria-label="A little encouragement"]')
  const title = carousel.locator('h2')
  const initialTitle = await title.textContent()
  await page.waitForTimeout(7_000)
  await expect(title).not.toHaveText(initialTitle ?? '')
})

test('mobile navigation opens and closes around route changes', async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 667 })
  await page.goto('/', { waitUntil: 'networkidle' })

  const toggle = page.getByRole('button', { name: 'Open navigation menu' })
  await expect(toggle).toBeVisible({ timeout: 110_000 })
  await toggle.click()
  await expect(page.getByRole('button', { name: 'Close navigation menu' })).toBeVisible()
  await page.getByRole('link', { name: 'Community', exact: true }).click()
  await expect(page).toHaveURL(/\/community$/)
  await expect(page.getByRole('button', { name: 'Open navigation menu' })).toBeVisible()
})

test('generated game artwork renders without broken images', async ({ page }) => {
  await page.goto('/', { waitUntil: 'networkidle' })
  const bingo = page.locator('img[src="/assets/game-bingo.png"]')
  await expect(bingo).toBeVisible({ timeout: 110_000 })
  await expect.poll(() => bingo.evaluate((image) => (image as HTMLImageElement).naturalWidth)).toBeGreaterThan(0)
})
