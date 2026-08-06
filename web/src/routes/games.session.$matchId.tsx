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
  return <section className="mini-game-card"><div className="ludo-track">{Array.from({ length: 28 }, (_, index) => <span className={index % 7 === 0 ? 'ludo-space ludo-space--safe' : 'ludo-space'} key={index}>{index === 0 && 'START'}</span>)}</div><div className="token-row">{state.positions?.[0]?.map((position: number, index: number) => <button className="game-token game-token--peach" type="button" disabled={state.current_player !== 0 || state.winner !== null} onClick={() => send({ token: index })} key={index}>●<small>{position < 0 ? 'Base' : position === 56 ? 'Home' : position}</small></button>)}</div><div className="game-action-row"><DiceFive size={21} /><span>{state.roll ? `You rolled ${state.roll}` : 'Choose a token to roll and move'}</span></div></section>
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
