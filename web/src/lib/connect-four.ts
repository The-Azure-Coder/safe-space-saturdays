type ConnectFourPlayer = {
  name: string
  is_bot: boolean
}

export function connectFourSeat(
  players: Array<ConnectFourPlayer>,
  seat: 1 | 2,
  viewerSeat: 1 | 2,
) {
  const player = players[seat - 1]
  return {
    disc: seat === 1 ? 'coral' : 'sunshine',
    name: player.name,
    isBot: player.is_bot,
    isViewer: seat === viewerSeat,
  }
}
