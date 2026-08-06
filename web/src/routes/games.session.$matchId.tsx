import { useEffect, useRef, useState } from 'react'
import { createFileRoute, Link, useParams } from '@tanstack/react-router'
import { ArrowLeft, DiceFive, Sparkle, Trophy } from '@phosphor-icons/react'

import { API_URL, api } from '../lib/api'
import type { GameSession } from '../lib/api'

export const Route = createFileRoute('/games/session/$matchId')({ component: GameSessionScreen })

function GameSessionScreen() {
  const { matchId } = useParams({ from: '/games/session/$matchId' })
  const [match, setMatch] = useState<GameSession | null>(null)
  const [error, setError] = useState('')
  const socket = useRef<WebSocket | null>(null)
  useEffect(() => {
    let active = true
    void api.gameSession(matchId).then((value) => { if (active) setMatch(value) }).catch((reason: Error) => setError(reason.message))
    const connection = new WebSocket(`${API_URL.replace(/^http/, 'ws')}/api/games/sessions/${matchId}/ws`)
    socket.current = connection
    connection.onmessage = (event) => {
      const message = JSON.parse(event.data) as { type: string; match?: GameSession; detail?: string }
      if (message.type === 'state' && message.match) setMatch(message.match)
      if (message.type === 'error') setError(message.detail ?? 'That action was not accepted')
    }
    connection.onerror = () => setError('Connection lost. Refresh to reconnect.')
    return () => { active = false; connection.close() }
  }, [matchId])
  const send = (action: Record<string, unknown>) => {
    setError('')
    if (socket.current?.readyState === WebSocket.OPEN) socket.current.send(JSON.stringify({ type: 'action', action }))
    else void api.gameAction(matchId, action).then(setMatch).catch((reason: Error) => setError(reason.message))
  }
  const state = match?.state
  const title = match?.game === 'ludo' ? 'Ludo' : match?.game === 'dominoes' ? 'Block Dominoes' : match?.game === 'bingo' ? 'Bingo' : 'Trivia Battle'
  return <main className="page-content game-play-page">
    <Link className="text-link game-play-back" to="/games"><ArrowLeft size={17} /> Back to games</Link>
    <section className="game-play-header"><div><span className="eyebrow">Friendly match · {title}</span><h1>Play at your own pace</h1><p>Kind competition, clear rules, and a little room to breathe.</p></div><div className="game-play-badge"><Sparkle size={22} /> Playing with a friendly bot</div></section>
    {error && <p className="form-error" role="alert">{error}</p>}
    {state?.winner !== null && state?.winner !== undefined && <div className="game-result"><Trophy size={22} /> {state.winner === 0 ? 'You won this round!' : 'The bot won this round.'}</div>}
    {match?.game === 'ludo' && <LudoBoard state={state ?? {}} send={send} />}
    {match?.game === 'dominoes' && <DominoBoard state={state ?? {}} send={send} />}
    {match?.game === 'bingo' && <BingoBoard state={state ?? {}} send={send} />}
    {match?.game === 'trivia' && <TriviaBoard state={state ?? {}} send={send} />}
  </main>
}

function LudoBoard({ state, send }: { state: Record<string, any>; send: (action: Record<string, unknown>) => void }) {
  const [rolling, setRolling] = useState(false)
  const [movingToken, setMovingToken] = useState<number | null>(null)
  const [diceFace, setDiceFace] = useState(Number(state.roll) || 1)
  const previousBotPositions = useRef<Array<number>>(state.positions?.[1] ?? [])
  const botMoving = JSON.stringify(previousBotPositions.current) !== JSON.stringify(state.positions?.[1] ?? [])
  useEffect(() => {
    if (botMoving) {
      const timer = window.setTimeout(() => { previousBotPositions.current = state.positions?.[1] ?? [] }, 650)
      return () => window.clearTimeout(timer)
    }
    return undefined
  }, [botMoving, state.positions])
  const rollAndMove = (token: number) => {
    if (rolling || state.current_player !== 0 || state.winner !== null) return
    setRolling(true)
    setMovingToken(token)
    let ticks = 0
    const diceTimer = window.setInterval(() => {
      ticks += 1
      setDiceFace((ticks % 6) + 1)
      if (ticks >= 7) {
        window.clearInterval(diceTimer)
        send({ token })
        window.setTimeout(() => { setRolling(false); setMovingToken(null) }, 700)
      }
    }, 90)
  }
  const positions = state.positions ?? [Array(4).fill(-1), Array(4).fill(-1)]
  return <section className="ludo-game-card">
    <div className="ludo-player-bar">
      <div className="ludo-player ludo-player--you"><span className="ludo-avatar">You</span><div><strong>You</strong><small>{state.current_player === 0 ? 'Your turn' : 'Waiting for the bot'}</small></div></div>
      <div className="ludo-player ludo-player--bot"><span className="ludo-avatar">MB</span><div><strong>Milo Bot</strong><small>{botMoving ? 'Rolling and moving…' : state.current_player === 1 ? 'Bot turn' : 'Ready to play'}</small></div><span className={botMoving ? 'bot-status bot-status--active' : 'bot-status'} aria-label={botMoving ? 'Bot is active' : 'Bot is ready'} /></div>
    </div>
    <div className="ludo-board-wrap">
      <div className="ludo-board" role="grid" aria-label="Ludo board">
        <div className="ludo-home ludo-home--you"><span>Your home</span>{positions[0]?.map((position: number, index: number) => <button className={movingToken === index ? 'ludo-piece ludo-piece--you ludo-piece--moving' : 'ludo-piece ludo-piece--you'} type="button" aria-label={`Your piece ${index + 1}, ${pieceLabel(position)}`} disabled={state.current_player !== 0 || state.winner !== null || rolling} onClick={() => rollAndMove(index)} key={`you-${index}`}>●</button>)}</div>
        <div className="ludo-home ludo-home--bot"><span>Bot home</span>{positions[1]?.map((position: number, index: number) => <span className="ludo-piece ludo-piece--bot" aria-label={`Bot piece ${index + 1}, ${pieceLabel(position)}`} key={`bot-${index}`}>●</span>)}</div>
        <div className="ludo-track-grid">{LUDO_TRACK.map((coordinate, index) => <span className={index % 13 === 0 ? 'ludo-track-cell ludo-track-cell--safe' : 'ludo-track-cell'} style={{ gridRow: coordinate[0] + 1, gridColumn: coordinate[1] + 1 }} key={index}>{positions[0]?.some((position: number) => position >= 0 && position < 52 && position === index) && <span className="ludo-board-piece ludo-board-piece--you" />}{positions[1]?.some((position: number) => position >= 0 && position < 52 && position === index) && <span className="ludo-board-piece ludo-board-piece--bot" />}</span>)}</div>
        <div className="ludo-goal"><span>HOME</span><div className="ludo-goal-heart">✦</div></div>
      </div>
    </div>
    <div className="ludo-controls"><div className={rolling ? 'ludo-dice ludo-dice--rolling' : 'ludo-dice'} aria-label={`Dice shows ${diceFace}`}>{diceFace}</div><div><strong>{rolling ? 'Rolling the dice…' : botMoving ? 'Milo is making a move…' : state.current_player === 0 ? 'Choose a piece to roll and move' : 'Milo is thinking…'}</strong><small>Six gets a piece out of home. Exact roll reaches the finish.</small></div><button className="button button--primary" type="button" disabled={state.current_player !== 0 || rolling || state.winner !== null} onClick={() => rollAndMove(0)}><DiceFive size={19} /> Roll & move</button></div>
  </section>
}

const LUDO_TRACK: Array<[number, number]> = [
  ...Array.from({ length: 13 }, (_, column) => [1, column + 1] as [number, number]),
  ...Array.from({ length: 12 }, (_, row) => [row + 2, 13] as [number, number]),
  ...Array.from({ length: 12 }, (_, column) => [13, 12 - column] as [number, number]),
  ...Array.from({ length: 11 }, (_, row) => [12 - row, 1] as [number, number]),
  [6, 6], [7, 6], [8, 6], [7, 7],
]

function pieceLabel(position: number) {
  if (position < 0) return 'in home'
  if (position >= 56) return 'finished'
  return `on space ${position + 1}`
}

function DominoBoard({ state, send }: { state: Record<string, any>; send: (action: Record<string, unknown>) => void }) {
  return <section className="mini-game-card"><div className="domino-table">{state.board?.length ? state.board.map((tile: Array<number>, index: number) => <span className="domino-tile domino-tile--table" key={index}>{tile.join(' · ')}</span>) : <p>Play a matching tile to start the line.</p>}</div><div className="domino-hand"><strong>Your hand</strong>{state.hands?.[0]?.map((tile: Array<number>, index: number) => <button className="domino-tile" type="button" key={index} disabled={state.current_player !== 0 || state.winner !== null} onClick={() => send({ tile_index: index, side: 'right' })}>{tile.join(' · ')}</button>)}<button className="button button--secondary button--small" type="button" onClick={() => send({ pass: true })}>Pass</button></div></section>
}

function BingoBoard({ state, send }: { state: Record<string, any>; send: (action: Record<string, unknown>) => void }) {
  return <section className="mini-game-card"><div className="bingo-head"><span>Drawn: {state.drawn?.length ?? 0}/75</span><button className="button button--primary button--small" type="button" onClick={() => send({ action: 'draw' })}>Draw ball</button><button className="button button--secondary button--small" type="button" onClick={() => send({ action: 'claim' })}>Claim Bingo</button></div><div className="bingo-card">{state.card?.flatMap((row: Array<number>, rowIndex: number) => row.map((number: number, colIndex: number) => <span className={state.marked?.[rowIndex]?.[colIndex] ? 'bingo-cell bingo-cell--marked' : 'bingo-cell'} key={`${rowIndex}-${colIndex}`}>{number || 'FREE'}</span>))}</div></section>
}

function TriviaBoard({ state, send }: { state: Record<string, any>; send: (action: Record<string, unknown>) => void }) {
  return <section className="mini-game-card trivia-card"><span className="eyebrow">Question {(state.question_index ?? 0) + 1} of 5</span><h2>{state.question}</h2><div className="trivia-options">{state.options?.map((option: string, index: number) => <button className="button button--secondary" type="button" disabled={state.answered} onClick={() => send({ answer: index })} key={option}>{option}</button>)}</div><div className="score-line"><span>You {state.scores?.[0] ?? 0}</span><span>Bot {state.scores?.[1] ?? 0}</span></div></section>
}
