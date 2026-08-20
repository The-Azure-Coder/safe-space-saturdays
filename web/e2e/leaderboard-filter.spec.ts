import { expect, test } from '@playwright/test'

test('leaderboard defaults to Today', async ({ page }) => {
  await page.route('**/health/ready**', (route) =>
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ status: 'ready' }) }),
  )
  await page.route('**/api/system/ready**', (route) =>
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ status: 'ready' }) }),
  )
  await page.route('**/api/auth/me', (route) =>
    route.fulfill({
      contentType: 'application/json',
      body: JSON.stringify({
        id: 21,
        name: 'Leaderboard Player',
        email: 'leaderboard@example.com',
        avatar_url: null,
        is_online: true,
        role: 'member',
        xp: 100,
        streak: 1,
        level: 1,
        is_approved: true,
        email_notifications_enabled: true,
      }),
    }),
  )
  await page.route('**/api/leaderboard?*', (route) =>
    route.fulfill({ contentType: 'application/json', body: '[]' }),
  )
  await page.route('**/api/leaderboard/me?*', (route) =>
    route.fulfill({ contentType: 'application/json', body: JSON.stringify({ rank: 1, user: { xp: 100 } }) }),
  )

  await page.goto('/leaderboard')
  await page.waitForFunction(() => document.documentElement.dataset.clientReady === 'true')
  await expect(page.getByRole('button', { name: 'Today' })).toHaveAttribute('aria-pressed', 'true')
  await expect(page.getByRole('button', { name: 'This Week' })).toHaveAttribute('aria-pressed', 'false')
})
