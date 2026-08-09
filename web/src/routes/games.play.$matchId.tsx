import { useEffect, useMemo, useRef, useState } from 'react'
import { createFileRoute, Link, useParams } from '@tanstack/react-router'
import { ArrowLeft, CaretDown, Robot, Sparkle, Trophy, UserCircle } from '@phosphor-icons/react'

import { API_URL, api } from '../lib/api'
import type { Match } from '../lib/api'

export const Route = createFileRoute('/games/play/$matchId')({ component: ConnectFourScreen })

const EMPTY_BOARD = Array.from({ length: 6 }, () => Array<number>(7).fill(0))

function ConnectFourScreen() {
  const { matchId } = useParams({ from: '/games/play/$matchId' })
  const [match, setMatch] = useState<Match | null>(null)
  const [error, setError] = useState('')
  const [pendingColumn, setPendingColumn] = useState<number | null>(null)
  const [hoveredColumn, setHoveredColumn] = useState<number | null>(null)
  const [ending, setEnding] = useState(false)
  const socket = useRef<WebSocket | null>(null)

  useEffect(() => {
    let active = true
    void api.match(matchId).then((value) => { if (active) setMatch(value) }).catch((reason: Error) => setError(reason.message))
    const connection = new WebSocket(`${API_URL.replace(/^http/, 'ws')}/api/games/matches/${matchId}/ws`)
    socket.current = connection
    connection.onmessage = (event) => {
      try {
        const message = JSON.parse(String(event.data)) as { type: string; state?: Match; detail?: string }
        if (message.type === 'state' && message.state) {
          setMatch(message.state)
          setPendingColumn(null)
        }
        if (message.type === 'error') {
          setError(message.detail ?? 'That move was not accepted')
          setPendingColumn(null)
        }
      } catch {
        setError('The game sent an unreadable update. Please refresh.')
      }
    }
    connection.onerror = () => setError('Connection lost. Your board is safe — refresh to reconnect.')
    return () => { active = false; connection.close() }
  }, [matchId])

  const board = match?.board ?? EMPTY_BOARD
  const winning = useMemo(() => new Set((match?.winning_cells ?? []).map(([row, column]) => `${row}-${column}`)), [match?.winning_cells])
  let previewRow: number | null = null
  if (hoveredColumn !== null) {
    for (let row = board.length - 1; row >= 0; row -= 1) {
      if (board[row][hoveredColumn] === 0) { previewRow = row; break }
    }
  }
  const canPlay = Boolean(match && match.current_player === 1 && !match.winner && !match.draw && pendingColumn === null)
  const status = match?.winner
    ? match.winner === 1 ? 'Four in a row — you won!' : 'Milo found four this time.'
    : match?.draw ? 'Every space filled. A thoughtful draw.'
      : match?.current_player === 1 ? 'Your turn — choose a column.' : 'Milo is thinking…'

  const play = (column: number) => {
    if (!canPlay || board[0][column] !== 0) return
    setError('')
    setPendingColumn(column)
    if (socket.current?.readyState === WebSocket.OPEN) {
      socket.current.send(JSON.stringify({ type: 'move', column }))
      return
    }
    void api.move(matchId, column).then(setMatch).catch((reason: Error) => setError(reason.message)).finally(() => setPendingColumn(null))
  }
  const playAgain = () => {
    setError('')
    if (socket.current?.readyState === WebSocket.OPEN) socket.current.send(JSON.stringify({ type: 'play_again' }))
  }
  const endSession = async () => {
    if (!match || !window.confirm('End this game session and delete its room? This cannot be undone.')) return
    setEnding(true)
    try {
      await api.endRoom(match.room_id)
      window.location.href = '/games'
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Only the room host can end this session.')
      setEnding(false)
    }
  }

  return <main className="page-content game-play-page connect-four-page">
    <div className="game-play-actions"><Link className="text-link game-play-back" to="/games"><ArrowLeft size={17} /> Back to games</Link><button className="button button--small button--danger" type="button" disabled={ending} onClick={() => void endSession()}>{ending ? 'Ending…' : 'End session'}</button></div>
    <section className="game-play-header">
      <div><span className="eyebrow">Friendly match · Connect Four</span><h1>Make a line. Take your time.</h1><p>Plan a step ahead and enjoy a bright little game break.</p></div>
      <div className="game-play-badge"><Sparkle size={20} weight="fill" /><span>{match?.move_count ?? 0} of 42 spaces played</span></div>
    </section>
    {error && <p className="form-error" role="alert">{error}</p>}

    <section className="connect-four-shell" aria-label="Connect Four game">
      <div className="connect-four-scoreboard">
        <article className={`connect-four-player connect-four-player--you${match?.current_player === 1 && !match.winner ? ' connect-four-player--active' : ''}`}>
          <span className="connect-four-player__avatar"><UserCircle size={28} weight="fill" /></span>
          <span><small>Coral discs</small><strong>You</strong></span>
          <i aria-hidden="true" />
        </article>
        <div className="connect-four-round"><small>Round one</small><strong>{match?.winner || match?.draw ? 'Complete' : 'Playing'}</strong></div>
        <article className={`connect-four-player connect-four-player--bot${match?.current_player === 2 && !match.winner ? ' connect-four-player--active' : ''}`}>
          <i aria-hidden="true" />
          <span><small>Sunshine discs</small><strong>Milo Bot</strong></span>
          <span className="connect-four-player__avatar"><Robot size={27} weight="fill" /></span>
        </article>
      </div>

      <div className={`connect-four-status${match?.winner ? ' connect-four-status--winner' : ''}`} aria-live="polite">
        {match?.winner ? <Trophy size={22} weight="fill" /> : <span className="connect-four-status__pulse" aria-hidden="true" />}
        <strong>{status}</strong>
        {(match?.winner || match?.draw) && <button className="button button--small button--primary game-play-again" type="button" onClick={playAgain}>Play again</button>}
      </div>

      <div className="connect-four-stage">
        <div className="connect-four-drop-controls" aria-label="Choose a column">
          {Array.from({ length: 7 }, (_, column) => <button
            key={column}
            className="connect-four-drop-button"
            type="button"
            aria-label={`Drop coral disc in column ${column + 1}`}
            disabled={!canPlay || board[0][column] !== 0}
            onClick={() => play(column)}
            onFocus={() => setHoveredColumn(column)}
            onBlur={() => setHoveredColumn(null)}
            onMouseEnter={() => setHoveredColumn(column)}
            onMouseLeave={() => setHoveredColumn(null)}
          ><CaretDown size={20} weight="bold" /><span>{column + 1}</span></button>)}
        </div>
        <div className="connect-four-board-wrap">
          <div className="connect-four-board" role="grid" aria-label="Six row by seven column Connect Four board">
            {board.flatMap((row, rowIndex) => row.map((cell, column) => {
              const isLast = match?.last_move?.[0] === rowIndex && match.last_move[1] === column
              const isWinning = winning.has(`${rowIndex}-${column}`)
              return <span
                className={`connect-four-cell connect-four-cell--${cell}${isLast ? ' connect-four-cell--last' : ''}${isWinning ? ' connect-four-cell--winning' : ''}${hoveredColumn === column && previewRow === rowIndex ? ' connect-four-cell--preview' : ''}`}
                role="gridcell"
                key={`${rowIndex}-${column}`}
                aria-label={`Row ${rowIndex + 1}, column ${column + 1}: ${cell === 0 ? 'empty' : cell === 1 ? 'your coral disc' : 'Milo’s sunshine disc'}${isWinning ? ', winning disc' : ''}`}
              />
            }))}
          </div>
          <div className="connect-four-feet" aria-hidden="true"><span /><span /></div>
        </div>
      </div>

      <div className="connect-four-tip"><Sparkle size={18} weight="fill" /><p><strong>Small strategy:</strong> build from the centre and watch for diagonal lines. First to connect four wins.</p></div>
    </section>
  </main>
}
