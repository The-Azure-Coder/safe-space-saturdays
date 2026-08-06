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
