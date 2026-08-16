import { test } from '@playwright/test'

const referenceRoutes = [
  ['Home', '/'],
  ['Login', '/login'],
  ['Registration', '/registration'],
  ['Daily-Check-In', '/check-in'],
  ['Quotes', '/quotes'],
  ['Community', '/community'],
  ['Games', '/games'],
  ['Leaderboard', '/leaderboard'],
  ['Profile', '/profile'],
] as const

for (const [name, route] of referenceRoutes) {
  test(`capture ${name} reference viewport`, async ({ page }) => {
    await page.goto(route, { waitUntil: 'networkidle' })
    await page.screenshot({
      path: `test-results/visual/${name}.png`,
      fullPage: false,
    })
  })
}
