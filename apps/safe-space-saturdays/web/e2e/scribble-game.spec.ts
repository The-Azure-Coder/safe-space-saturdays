import { expect, request, test } from '@playwright/test'

test('Scribble room starts with bots and opens a playable drawing session', async () => {
  const client = await request.newContext({ baseURL: 'http://localhost:8000' })
  const password = 'scribble-room-e2e-password-123'
  try {
    const registration = await client.post('/api/auth/register', {
      data: {
        name: 'Scribble Room E2E',
        email: `scribble-room-${Date.now()}@example.com`,
        password,
        confirm_password: password,
      },
    })
    expect(registration.status()).toBe(201)
    const games = await client.get('/api/games?limit=100')
    expect(games.ok()).toBeTruthy()
    const scribble = (await games.json() as Array<{ id: number; name: string }>).find((game) => game.name === 'Scribble')
    expect(scribble).toBeTruthy()

    const roomResponse = await client.post('/api/games/rooms', { data: { game_id: scribble!.id, name: 'Scribble E2E Room', max_players: 2, fill_with_bots: true } })
    expect(roomResponse.status()).toBe(201)
    const room = await roomResponse.json() as { id: number }
    const sessionResponse = await client.post('/api/games/sessions', { data: { room_id: room.id, fill_with_bots: true } })
    expect(sessionResponse.status(), await sessionResponse.text()).toBe(201)
    const session = await sessionResponse.json() as { match_id: string; game: string; state: Record<string, any> }
    expect(session.game).toBe('scribble')
    expect(session.state.player_count).toBe(2)
    expect(session.state.current_drawer).toBe(0)

    const stroke = await client.post(`/api/games/sessions/${session.match_id}/actions`, { data: { action: { action: 'stroke', points: [{ x: 0.1, y: 0.1 }, { x: 0.8, y: 0.8 }] } } })
    expect(stroke.status()).toBe(200)
    const endTurn = await client.post(`/api/games/sessions/${session.match_id}/actions`, { data: { action: { action: 'end_turn' } } })
    expect(endTurn.status()).toBe(200)
    expect((await endTurn.json()).state.phase).toBe('guessing')
    expect((await client.delete(`/api/games/rooms/${room.id}`)).status()).toBe(204)
  } finally {
    await client.dispose()
  }
})
