import { describe, expect, it } from 'vitest'

import { connectFourSeat } from './connect-four'

const players = [
  { name: 'Host', is_bot: false },
  { name: 'Hugo', is_bot: false },
]

describe('connectFourSeat', () => {
  it('keeps the host coral and player two sunshine for the guest viewer', () => {
    expect(connectFourSeat(players, 1, 2)).toEqual({
      disc: 'coral',
      name: 'Host',
      isBot: false,
      isViewer: false,
    })
    expect(connectFourSeat(players, 2, 2)).toEqual({
      disc: 'sunshine',
      name: 'Hugo',
      isBot: false,
      isViewer: true,
    })
  })
})
