import { describe, expect, it } from 'vitest'

import { playerDisplayName } from './game-player'

describe('playerDisplayName', () => {
  it('marks the actual viewer instead of always marking the host seat', () => {
    expect(playerDisplayName('Host', 0, 1)).toBe('Host')
    expect(playerDisplayName('Hugo', 1, 1)).toBe('Hugo · You')
  })
})
