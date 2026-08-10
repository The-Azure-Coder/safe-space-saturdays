import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { api } from '../lib/api'

export function GameRoomControls({ roomId }: { roomId: number }) {
  const queryClient = useQueryClient()
  const [gameId, setGameId] = useState<number | ''>('')
  const room = useQuery({ queryKey: ['room', roomId], queryFn: () => api.room(roomId), enabled: roomId > 0 })
  const games = useQuery({ queryKey: ['games', 'room-controls'], queryFn: () => api.games(1, 50), enabled: roomId > 0 })
  const changeGame = useMutation({
    mutationFn: () => api.changeRoomGame(roomId, Number(gameId)),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['rooms'] })
      window.location.href = '/games'
    },
  })

  useEffect(() => {
    const current = games.data?.find((game) => game.name === room.data?.game)
    if (current) setGameId(current.id)
  }, [games.data, room.data?.game])

  if (!room.data?.is_host || room.data.status === 'closed' || !games.data?.length) return null
  const compatibleGames = games.data
  return <div className="game-room-controls">
    <span className="game-room-controls__label">Host controls</span>
    <select
      value={gameId}
      onChange={(event) => setGameId(Number(event.target.value))}
      aria-label="Choose a new game for this room"
      disabled={changeGame.isPending}
    >
      {compatibleGames.map((game) => <option value={game.id} key={game.id}>{game.name}</option>)}
    </select>
    <button
      className="button button--small button--secondary"
      type="button"
      disabled={changeGame.isPending || !gameId || games.data.find((game) => game.id === gameId)?.name === room.data.game}
      onClick={() => changeGame.mutate()}
    >
      {changeGame.isPending ? 'Changing…' : 'Change game'}
    </button>
    {changeGame.error && <span className="form-error" role="alert">{changeGame.error.message}</span>}
  </div>
}
