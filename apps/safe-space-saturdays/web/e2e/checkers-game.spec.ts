import { expect, test } from '@playwright/test'

test.setTimeout(180_000)

const initialCheckersBoard = () => Array.from({ length: 8 }, (_row, row) =>
  Array.from({ length: 8 }, (_cell, col) => {
    if ((row + col) % 2 !== 1) return 0
    if (row < 3) return 2
    if (row > 4) return 1
    return 0
  }),
)

test('Checkers is featured, launches with a bot, and stays usable on mobile', async ({ page }) => {
  const email = `checkers-e2e-${Date.now()}@example.com`
  const password = 'checkers-browser-password-123'

  await page.goto('/registration')
  await page.waitForFunction(() => document.documentElement.dataset.clientReady === 'true', undefined, { timeout: 110_000 })
  await page.getByLabel('Full name').fill('Checkers Browser Player')
  await page.getByLabel('Email').fill(email)
  await page.locator('input[name="password"]').fill(password)
  await page.locator('input[name="confirm-password"]').fill(password)
  await page.getByLabel(/I agree to the Safe Space Saturdays/).check()
  await page.getByRole('button', { name: 'Create account' }).click()
  await expect(page).toHaveURL(/\/$/)

  await page.goto('/games')
  const card = page.locator('.game-tile').filter({ hasText: 'Checkers' }).first()
  await expect(card).toBeVisible({ timeout: 110_000 })
  await card.getByRole('button', { name: 'Play' }).click()
  await expect(page).toHaveURL(/\/games\/session\/[a-f0-9-]+$/)

  const game = page.getByRole('region', { name: 'Checkers game' })
  await expect(game).toBeVisible({ timeout: 110_000 })
  await expect(game.getByText('Game level 1 · Win streak 0')).toBeVisible()
  await expect(page.getByRole('grid', { name: 'Checkers board' }).getByRole('gridcell')).toHaveCount(64)
  await expect(page.getByText('Captures are required')).toBeVisible()
  await page.setViewportSize({ width: 390, height: 844 })
  await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
})

test('a completed Checkers game can be played again', async ({ page }) => {
  const matchId = '00000000-0000-4000-8000-000000000001'
  const players = [
    { name: 'Checkers Browser Player', color: 'coral', is_bot: false },
    { name: 'Milo Bot', color: 'sage', is_bot: true },
  ]
  let receivedAction: Record<string, unknown> | undefined

  await page.addInitScript(() => {
    class ClosedWebSocket {
      static OPEN = 1
      readyState = 3
      close() {}
    }
    Object.defineProperty(window, 'WebSocket', { value: ClosedWebSocket })
  })
  await page.route('**/health/ready*', (route) => route.fulfill({
    status: 200, contentType: 'application/json', body: JSON.stringify({ status: 'ready' }),
  }))
  await page.route('**/api/auth/me', (route) => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({
      id: 999, name: 'Checkers Browser Player', email: 'checkers@example.com',
      avatar_url: null, is_online: true, role: 'member', xp: 0, streak: 0,
      level: 1, is_approved: true, email_notifications_enabled: false,
    }),
  }))
  await page.route(new RegExp(`/api/games/sessions/${matchId}(?:/actions)?(?:\\?.*)?$`), async (route) => {
    const isReplay = route.request().method() === 'POST'
    if (isReplay) receivedAction = route.request().postDataJSON().action
    const state = isReplay
      ? {
          game: 'checkers', current_player: 0, winner: null, draw: false,
          players, board: initialCheckersBoard(), chain_piece: null,
          legal_moves: [{ from: [5, 0], to: [4, 1], capture: null }],
          seat_index: 0, game_level: 1, game_streak: 1,
          last_event: 'Your turn. Select a piece to see its legal moves.',
        }
      : {
          game: 'checkers', current_player: 0, winner: 0, draw: false,
          players, board: [[0, 0, 0, 0, 0, 0, 0, 0], ...Array.from({ length: 7 }, () => Array(8).fill(0))],
          legal_moves: [], seat_index: 0, game_level: 1, game_streak: 1,
          last_event: 'Checkers Browser Player wins!',
        }
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ match_id: matchId, room_id: 999, game: 'checkers', state }),
    })
  })

  await page.goto(`/games/session/${matchId}`)
  const game = page.getByRole('region', { name: 'Checkers game' })
  await expect(game).toBeVisible({ timeout: 110_000 })
  await expect(page.getByText('You won this round!')).toBeVisible()

  await game.getByRole('button', { name: 'Play again' }).click()

  await expect.poll(() => receivedAction).toEqual({ action: 'play_again' })
  await expect(game.getByRole('button', { name: 'Play again' })).toBeHidden()
  await expect(game.getByText("Checkers Browser Player's turn")).toBeVisible()
  await expect(game.locator('.checkers-piece')).toHaveCount(24)
})
