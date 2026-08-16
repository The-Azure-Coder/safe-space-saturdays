import { expect, request, test } from '@playwright/test'

test.describe.configure({ timeout: 120_000 })

type Client = Awaited<ReturnType<typeof request.newContext>>

async function registeredClient(label: string): Promise<Client> {
  const client = await request.newContext({ baseURL: 'http://localhost:8000' })
  const password = 'multiplayer-e2e-password-123'
  const response = await client.post('/api/auth/register', {
    data: {
      name: `Multiplayer ${label}`,
      email: `multiplayer-${label}-${Date.now()}@example.com`,
      password,
      confirm_password: password,
    },
  })
  expect(response.status()).toBe(201)
  return client
}

async function startHumanRoom(host: Client, guest: Client, gameId: number, maxPlayers = 2) {
  const created = await host.post('/api/games/rooms', { data: { game_id: gameId, name: `Human ${Date.now()}`, max_players: maxPlayers, fill_with_bots: false } })
  expect(created.status()).toBe(201)
  const room = await created.json() as { id: number }
  const joined = await guest.post(`/api/games/rooms/${room.id}/join`)
  expect(joined.status()).toBe(200)
  expect((await guest.post(`/api/games/rooms/${room.id}/ready`)).status()).toBe(200)
  return room.id
}

test('two authenticated users can fill a human room and take turns in every game', async () => {
  const catalogueClient = await registeredClient('catalogue')
  const gamesResponse = await catalogueClient.get('/api/games?limit=20')
  expect(gamesResponse.ok()).toBeTruthy()
  const games = await gamesResponse.json() as Array<{ id: number; name: string }>
  await catalogueClient.dispose()

  for (const gameName of ['Connect Four', 'Ludo', 'Dominoes', 'Trivia Battle']) {
    const game = games.find((candidate) => candidate.name === gameName)
    expect(game, `Missing seeded game: ${gameName}`).toBeTruthy()
    const host = await registeredClient(`${gameName.replaceAll(' ', '-')}-host`)
    const guest = await registeredClient(`${gameName.replaceAll(' ', '-')}-guest`)
    const roomId = await startHumanRoom(host, guest, game!.id)

    if (gameName === 'Connect Four') {
      const started = await host.post('/api/games/matches', { data: { room_id: roomId, with_bot: false, bot_difficulty: 'friendly' } })
      expect(started.status()).toBe(201)
      const match = await started.json() as { match_id: string }
      expect((await host.post(`/api/games/matches/${match.match_id}/moves`, { data: { column: 0 } })).status()).toBe(200)
      expect((await guest.post(`/api/games/matches/${match.match_id}/moves`, { data: { column: 1 } })).status()).toBe(200)
    } else {
      const started = await host.post('/api/games/sessions', { data: { room_id: roomId, fill_with_bots: false } })
      expect(started.status()).toBe(201)
      const match = await started.json() as { match_id: string; state: Record<string, any> }
      if (gameName === 'Ludo') {
        let state = match.state
        for (let index = 0; index < 12 && state.current_player !== 1; index += 1) {
          const action = state.phase === 'move' ? { action: 'move', token: state.legal_tokens[0] } : { action: 'roll' }
          const response = await host.post(`/api/games/sessions/${match.match_id}/actions`, { data: { action } })
          expect(response.status()).toBe(200)
          state = (await response.json()).state
        }
        expect(state.current_player).toBe(1)
        const guestAction = state.phase === 'move' ? { action: 'move', token: state.legal_tokens[0] } : { action: 'roll' }
        expect((await guest.post(`/api/games/sessions/${match.match_id}/actions`, { data: { action: guestAction } })).status()).toBe(200)
      } else if (gameName === 'Dominoes') {
        const hostMove = match.state.legal_moves[0]
        expect((await host.post(`/api/games/sessions/${match.match_id}/actions`, { data: { action: hostMove } })).status()).toBe(200)
        const guestState = (await (await guest.get(`/api/games/sessions/${match.match_id}`)).json()).state
        const guestLegalMove = guestState.legal_moves[0]
        const guestMove = await guest.post(`/api/games/sessions/${match.match_id}/actions`, { data: { action: { tile_index: guestLegalMove.tile_index, side: guestLegalMove.sides[0] } } })
        expect(await guestMove.text()).toContain('match_id')
      } else {
        expect((await host.post(`/api/games/sessions/${match.match_id}/actions`, { data: { action: { answer: 0 } } })).status()).toBe(200)
        expect((await guest.post(`/api/games/sessions/${match.match_id}/actions`, { data: { action: { answer: 0 } } })).status()).toBe(200)
      }
    }
    expect((await host.delete(`/api/games/rooms/${roomId}`)).status()).toBe(204)
    await host.dispose()
    await guest.dispose()
  }
})
