import { expect, test } from '@playwright/test'

const member = {
  id: 7,
  name: 'Challenge Member',
  email: 'challenge@example.com',
  avatar_url: null,
  is_online: true,
  role: 'member',
  is_approved: true,
  xp: 100,
  streak: 2,
  level: 1,
}

test('a member can choose and complete a weekly challenge', async ({ page }) => {
  let completed = false
  const challenge = {
    id: 1,
    slug: 'notice-beauty',
    title: 'Notice something beautiful',
    description: 'Pause and notice one small detail that brings you joy.',
    category: 'Notice',
    icon: '🌼',
    color: 'sage',
    xp: 10,
    week_start: '2026-08-10',
    active_until: '2026-08-16',
    completed: false,
    completed_at: null,
    reflection: null,
  }
  const challengeResponse = () => ({
    week_start: '2026-08-10',
    active_until: '2026-08-16',
    completed_count: completed ? 1 : 0,
    total_count: 1,
    xp_earned: completed ? 10 : 0,
    challenges: [{ ...challenge, completed }],
  })

  await page.route('**/api/auth/me', (route) =>
    route.fulfill({ contentType: 'application/json', body: JSON.stringify(member) }),
  )
  await page.route('**/api/challenges/current*', (route) =>
    route.fulfill({ contentType: 'application/json', body: JSON.stringify(challengeResponse()) }),
  )
  await page.route('**/api/challenges/1/complete', async (route) => {
    completed = true
    await route.fulfill({ contentType: 'application/json', body: JSON.stringify({ ...challenge, completed: true, completed_at: '2026-08-13T12:00:00Z', reflection: 'A warm patch of sunlight.' }) })
  })

  await page.goto('/challenges')
  await expect(page.getByRole('heading', { name: /Your weekly challenges/ })).toBeVisible({ timeout: 30_000 })
  await page.getByRole('button', { name: 'I’m ready' }).click()
  await page.getByLabel('Add a note').fill('A warm patch of sunlight.')
  await page.getByRole('button', { name: 'Complete · +10 XP' }).click()
  await expect(page.getByRole('status', { name: 'Challenge completed' })).toContainText('Challenge complete · +10 XP')
  await expect(page.getByText('1 of 1')).toBeVisible()
  await expect(page.getByText('Completed', { exact: true })).toBeVisible()
})
