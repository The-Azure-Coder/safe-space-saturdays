import { expect, test } from '@playwright/test'

test('a member can open an active room with the eye action and watch read-only', async ({ page }) => {
  await page.route('**/health/ready**', (route) => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ status: 'ready' }) }))
  await page.route('**/api/system/ready**', (route) => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ status: 'ready' }) }))
  await page.route('**/*', async (route) => {
    if (route.request().url().includes('/health/ready') || route.request().url().includes('/api/system/ready')) {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ status: 'ready' }) })
      return
    }
    await route.continue()
  })
  await page.route('**/api/auth/me', (route) => route.fulfill({ contentType: 'application/json', body: JSON.stringify({ id: 9, name: 'Spectator', email: 'spectator@example.com', avatar_url: null, is_online: true, role: 'member', xp: 0, streak: 0, level: 1, is_approved: true, email_notifications_enabled: true }) }))
  await page.route('**/api/games?page**', (route) => route.fulfill({ contentType: 'application/json', body: '[]' }))
  await page.route('**/api/games/rooms?page**', (route) => route.fulfill({ contentType: 'application/json', body: JSON.stringify([{ id: 14, name: 'Saturday Checkers', game: 'Checkers', players: 2, max_players: 2, status: 'active', joined: false, is_host: false, match_id: 'match-1', ready: false, fill_with_bots: false, bot_difficulty: 'friendly', invite_token: null }]) }))
  await page.route('**/api/games/winners?page**', (route) => route.fulfill({ contentType: 'application/json', body: '[]' }))
  await page.route('**/api/games/sessions/match-1?*', (route) => route.fulfill({ contentType: 'application/json', body: JSON.stringify({ match_id: 'match-1', room_id: 14, game: 'checkers', spectator: true, state: { board: Array.from({ length: 8 }, () => Array(8).fill(0)), current_player: 0, winner: null, draw: false, players: [{ name: 'Host', color: 'coral', is_bot: false }, { name: 'Guest', color: 'sage', is_bot: false }], legal_moves: [], seat_index: -1, game_level: 2, game_streak: 1 } }) }))

  await page.goto('/games')
  await page.getByRole('button', { name: 'Watch Saturday Checkers' }).click()
  await expect(page).toHaveURL(/\/games\/session\/match-1$/)
  await expect(page.getByRole('status')).toContainText('spectating')
  await expect(page.getByRole('button', { name: 'End session' })).toHaveCount(0)
})
