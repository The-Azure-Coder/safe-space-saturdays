import { useEffect, useMemo, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { createFileRoute, Link, useParams } from '@tanstack/react-router'
import { ArrowLeft, CaretDown, Eye, Robot, Sparkle, Trophy, UserCircle } from '@phosphor-icons/react'

import { GeneralLoader } from '../components/general-loader'
import { API_URL, api, apiRetryDelay, shouldRetryApiRequest } from '../lib/api'
import type { Match } from '../lib/api'
import { connectFourSeat } from '../lib/connect-four'
import { openReconnectingGameSocket } from '../lib/game-websocket'
import { GameRoomControls } from '../components/game-room-controls'

export const Route = createFileRoute('/games/play/$matchId')({ component: ConnectFourScreen })

const EMPTY_BOARD = Array.from({ length: 6 }, () => Array<number>(7).fill(0))

function ConnectFourScreen() {
  const { matchId } = useParams({ from: '/games/play/$matchId' })
  const [match, setMatch] = useState<Match | null>(null)
  const [error, setError] = useState('')
  const [connectionNotice, setConnectionNotice] = useState('')
  const [pendingColumn, setPendingColumn] = useState<number | null>(null)
  const [hoveredColumn, setHoveredColumn] = useState<number | null>(null)
  const [ending, setEnding] = useState(false)
  const socket = useRef<WebSocket | null>(null)
  const matchQuery = useQuery({
    queryKey: ['connect-four-match', matchId],
    queryFn: () => api.match(matchId),
    retry: shouldRetryApiRequest,
    retryDelay: apiRetryDelay,
  })

  useEffect(() => {
    if (!matchQuery.data) return
    setMatch(matchQuery.data)
    setError('')
  }, [matchQuery.data])

  useEffect(() => {
    if (!matchQuery.data) return
    return openReconnectingGameSocket({
      url: `${API_URL.replace(/^http/, 'ws')}/api/games/matches/${matchId}/ws`,
      onSocket: (connection) => { socket.current = connection },
      onStatus: (status, detail) => {
        setConnectionNotice(status === 'connected' ? '' : detail ?? (status === 'connecting' ? 'Connecting to live game…' : 'Connection interrupted. Reconnecting…'))
      },
      onResync: async () => setMatch(await api.match(matchId)),
      onMessage: (rawMessage) => {
        const message = rawMessage as { type: string; state?: Match; spectator_count?: number; detail?: string }
        if (message.type === 'state' && message.state) {
          const nextState = message.state
          setMatch((current) => ({ ...nextState, player: nextState.player ?? current?.player ?? 1, spectator: nextState.spectator, spectator_count: message.spectator_count ?? nextState.spectator_count }))
          setPendingColumn(null)
        }
        if (message.type === 'spectator_count') setMatch((current) => current ? { ...current, spectator_count: message.spectator_count ?? 0 } : current)
        if (message.type === 'session_ended') window.location.href = '/games'
        if (message.type === 'game_changed') window.location.href = '/games'
        if (message.type === 'error') {
          setError(message.detail ?? 'That move was not accepted')
          setPendingColumn(null)
        }
      },
    })
  }, [matchId, matchQuery.data])

  const board = match?.board ?? EMPTY_BOARD
  const winning = useMemo(() => new Set((match?.winning_cells ?? []).map(([row, column]) => `${row}-${column}`)), [match?.winning_cells])
  if (!match && matchQuery.isPending)
    return <main className="page-content game-play-page connect-four-page"><GeneralLoader label="Loading your game…" /></main>
  if (!match && matchQuery.isError)
    return <main className="page-content game-play-page connect-four-page"><GeneralLoader label="Reconnecting to your game…" onRetry={() => void matchQuery.refetch()} /></main>
  let previewRow: number | null = null
  if (hoveredColumn !== null) {
    for (let row = board.length - 1; row >= 0; row -= 1) {
      if (board[row][hoveredColumn] === 0) { previewRow = row; break }
    }
  }
  const playerNumber = match?.player ?? 1
  const isSpectator = Boolean(match?.spectator)
  const players = match?.players.length === 2
    ? match.players
    : [{ name: 'You', is_bot: false }, { name: 'Milo Bot', is_bot: true }]
  const coralSeat = connectFourSeat(players, 1, playerNumber)
  const sunshineSeat = connectFourSeat(players, 2, playerNumber)
  const ownDiscLabel = playerNumber === 1 ? coralSeat.disc : sunshineSeat.disc
  const canPlay = Boolean(!isSpectator && match && match.current_player === playerNumber && !match.winner && !match.draw && pendingColumn === null)
  const status = match?.winner
    ? isSpectator ? `${players[match.winner - 1]?.name ?? 'A player'} found four this time.` : match.winner === playerNumber ? 'Four in a row — you won!' : `${players[match.winner - 1]?.name ?? 'Your opponent'} found four this time.`
    : match?.draw ? 'Every space filled. A thoughtful draw.'
      : isSpectator ? `${players[(match?.current_player ?? 1) - 1]?.name ?? 'A player'} is thinking…` : match?.current_player === playerNumber ? 'Your turn — choose a column.' : `${players[(match?.current_player ?? 1) - 1]?.name ?? 'Your opponent'} is thinking…`

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
    if (isSpectator || !match || !window.confirm('End this game session and delete its room? This cannot be undone.')) return
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
    <div className="game-play-actions"><Link className="text-link game-play-back" to="/games"><ArrowLeft size={17} /> Back to games</Link>{!isSpectator && <div className="game-play-actions__right"><GameRoomControls roomId={match?.room_id ?? 0} /><button className="button button--small button--danger" type="button" disabled={ending} onClick={() => void endSession()}>{ending ? 'Ending…' : 'End session'}</button></div>}</div>
    <section className="game-play-header">
      <div><span className="eyebrow">Friendly match · Connect Four</span><h1>Make a line. Take your time.</h1><p>Plan a step ahead and enjoy a bright little game break.</p><small className="game-level-badge">Game level {match?.game_level ?? 1} · Win streak {match?.game_streak ?? 0}</small></div>
      <div className="game-play-badge"><Sparkle size={20} weight="fill" /><span>{match?.move_count ?? 0} of 42 spaces played</span>{(match?.spectator_count ?? 0) > 0 && <span className="spectator-count" aria-label={`${match?.spectator_count} people watching`}><Eye size={17} aria-hidden="true" /> {match?.spectator_count}</span>}</div>
    </section>
    {isSpectator && <p className="spectator-banner" role="status"><Eye size={18} aria-hidden="true" /> You are spectating this live game. The board is read-only.</p>}
    {connectionNotice && <p className="spectator-banner" role="status">{connectionNotice}</p>}
    {error && <p className="form-error" role="alert">{error}</p>}

    <section className="connect-four-shell" aria-label="Connect Four game">
      <div className="connect-four-scoreboard">
        <article className={`connect-four-player connect-four-player--you${match?.current_player === 1 && !match.winner ? ' connect-four-player--active' : ''}`}>
          <span className="connect-four-player__avatar"><UserCircle size={28} weight="fill" /></span>
          <span><small>Coral discs</small><strong>{coralSeat.name}{coralSeat.isViewer ? ' · You' : ''}</strong></span>
          <i aria-hidden="true" />
        </article>
        <div className="connect-four-round"><small>Round one</small><strong>{match?.winner || match?.draw ? 'Complete' : 'Playing'}</strong></div>
        <article className={`connect-four-player connect-four-player--bot${match?.current_player === 2 && !match.winner ? ' connect-four-player--active' : ''}`}>
          <i aria-hidden="true" />
          <span><small>Sunshine discs</small><strong>{sunshineSeat.name}{sunshineSeat.isViewer ? ' · You' : ''}</strong></span>
          <span className="connect-four-player__avatar">{sunshineSeat.isBot ? <Robot size={27} weight="fill" /> : <UserCircle size={27} weight="fill" />}</span>
        </article>
      </div>

      <div className={`connect-four-status${match?.winner ? ' connect-four-status--winner' : ''}`} aria-live="polite">
        {match?.winner ? <Trophy size={22} weight="fill" /> : <span className="connect-four-status__pulse" aria-hidden="true" />}
        <strong>{status}</strong>
        {(match?.winner || match?.draw) && !isSpectator && <button className="button button--small button--primary game-play-again" type="button" onClick={playAgain}>Play again</button>}
      </div>

      <div className="connect-four-stage">
        <div className="connect-four-drop-controls" aria-label="Choose a column">
          {Array.from({ length: 7 }, (_, column) => <button
            key={column}
            className="connect-four-drop-button"
            type="button"
            aria-label={`Drop ${ownDiscLabel} disc in column ${column + 1}`}
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
                aria-label={`Row ${rowIndex + 1}, column ${column + 1}: ${cell === 0 ? 'empty' : cell === 1 ? 'coral disc' : 'sunshine disc'}${isWinning ? ', winning disc' : ''}`}
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
