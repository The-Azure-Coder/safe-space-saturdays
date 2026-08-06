import { useEffect, useRef, useState } from 'react'
import { createFileRoute, Link, useParams } from '@tanstack/react-router'
import { ArrowLeft, Robot, Trophy } from '@phosphor-icons/react'

import { API_URL, api } from '../lib/api'
import type { Match } from '../lib/api'

export const Route = createFileRoute('/games/play/$matchId')({ component: ConnectFourScreen })

function ConnectFourScreen() {
  const { matchId } = useParams({ from: '/games/play/$matchId' })
  const [match, setMatch] = useState<Match | null>(null)
  const [error, setError] = useState('')
  const socket = useRef<WebSocket | null>(null)

  useEffect(() => {
    let active = true
    void api.match(matchId).then((value) => { if (active) setMatch(value) }).catch((reason: Error) => setError(reason.message))
    const wsUrl = `${API_URL.replace(/^http/, 'ws')}/api/games/matches/${matchId}/ws`
    const connection = new WebSocket(wsUrl)
    socket.current = connection
    connection.onmessage = (event) => {
      const message = JSON.parse(event.data) as { type: string; state?: Match; detail?: string }
      if (message.type === 'state' && message.state) setMatch(message.state)
      if (message.type === 'error') setError(message.detail ?? 'That move was not accepted')
    }
    connection.onerror = () => setError('Connection lost. Refresh to reconnect.')
    return () => { active = false; connection.close() }
  }, [matchId])

  const play = (column: number) => {
    if (!match || match.winner || match.draw) return
    setError('')
    if (socket.current?.readyState === WebSocket.OPEN) socket.current.send(JSON.stringify({ type: 'move', column }))
    else void api.move(matchId, column).then(setMatch).catch((reason: Error) => setError(reason.message))
  }

  return <main className="page-content game-play-page">
    <Link className="text-link game-play-back" to="/games"><ArrowLeft size={17} /> Back to games</Link>
    <section className="game-play-header"><div><span className="eyebrow">Friendly match · Connect Four</span><h1>Take a thoughtful pause</h1><p>Drop a disc, look for a line, and enjoy the little win.</p></div><div className="game-play-badge"><Robot size={22} /><span>Playing with a friendly bot</span></div></section>
    {error && <p className="form-error" role="alert">{error}</p>}
    <section className="connect-four-card" aria-label="Connect Four board">
      <div className="connect-four-status">{match?.winner ? <><Trophy size={20} /> {match.winner === 1 ? 'You' : 'The bot'} won this round.</> : match?.draw ? 'A gentle draw. Nice work.' : match?.current_player === 1 ? 'Your turn — choose a column.' : 'The bot is thinking…'}</div>
      <div className="connect-four-columns" aria-label="Choose a column">
        {Array.from({ length: 7 }, (_, column) => <button key={column} className="connect-four-column" type="button" aria-label={`Drop disc in column ${column + 1}`} disabled={!match || match.current_player !== 1 || Boolean(match.winner) || match.draw} onClick={() => play(column)}>{column + 1}</button>)}
      </div>
      <div className="connect-four-board" role="grid" aria-label="Connect Four board">
        {(match?.board ?? Array.from({ length: 6 }, () => Array(7).fill(0))).flatMap((row, rowIndex) => row.map((cell, column) => <span className={`connect-four-cell connect-four-cell--${cell}`} role="gridcell" key={`${rowIndex}-${column}`} aria-label={cell === 0 ? 'Empty' : cell === 1 ? 'Your disc' : 'Bot disc'} />))}
      </div>
      <p className="game-play-help">Classic rules: first to four discs horizontally, vertically, or diagonally wins.</p>
    </section>
  </main>
}
