import { useEffect, useRef, useState } from 'react'
import { createFileRoute, Link, useParams } from '@tanstack/react-router'
import { ArrowLeft, Sparkle, Trophy } from '@phosphor-icons/react'

import { LudoGame } from '../components/ludo-game'
import type { LudoState } from '../components/ludo-game'
import { DominoGame } from '../components/domino-game'
import type { DominoState } from '../components/domino-game'
import { TriviaGame } from '../components/trivia-game'
import type { TriviaState } from '../components/trivia-game'
import { ScribbleGame } from '../components/scribble-game'
import type { ScribbleState } from '../components/scribble-game'
import { API_URL, api } from '../lib/api'
import type { GameSession } from '../lib/api'

export const Route = createFileRoute('/games/session/$matchId')({ component: GameSessionScreen })

function GameSessionScreen() {
  const { matchId } = useParams({ from: '/games/session/$matchId' })
  const [match, setMatch] = useState<GameSession | null>(null)
  const viewerSeat = useRef(0)
  const [error, setError] = useState('')
  const [ending, setEnding] = useState(false)
  const socket = useRef<WebSocket | null>(null)
  useEffect(() => {
    let active = true
    void api.gameSession(matchId).then((value) => {
      viewerSeat.current = Number(value.state.seat_index ?? 0)
      if (active) setMatch(value)
    }).catch((reason: Error) => setError(reason.message))
    const connection = new WebSocket(`${API_URL.replace(/^http/, 'ws')}/api/games/sessions/${matchId}/ws`)
    socket.current = connection
    connection.onmessage = (event) => {
      const message = JSON.parse(event.data) as { type: string; match?: GameSession; detail?: string }
      if (message.type === 'drawing_segment' && (message as { segment?: ScribbleState['live_stroke'] }).segment) {
        const segment = (message as { segment: ScribbleState['live_stroke'] }).segment
        setMatch((current) => current ? { ...current, state: { ...current.state, live_stroke: segment } } : current)
      }
      if (message.type === 'state' && message.match) {
        const nextMatch = message.match
        if (nextMatch.state.seat_index === undefined) {
          nextMatch.state.seat_index = viewerSeat.current
        } else {
          viewerSeat.current = Number(nextMatch.state.seat_index)
        }
        setMatch(nextMatch)
      }
      if (message.type === 'session_ended') window.location.href = '/games'
      if (message.type === 'game_changed') window.location.href = '/games'
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
  const state = match?.state
  const title = match?.game === 'ludo' ? 'Ludo' : match?.game === 'dominoes' ? 'Block Dominoes' : match?.game === 'bingo' ? 'Bingo' : match?.game === 'scribble' ? 'Scribble' : 'Trivia Battle'
  const isTrivia = match?.game === 'trivia'
  const players = state?.players ?? []
  const seat = Number(state?.seat_index ?? 0)
  const opponents = players.filter((_player: { name: string; is_bot: boolean }, index: number) => index !== seat)
  const opponentLabel = opponents.length
    ? opponents.map((player: { name: string; is_bot: boolean }) => player.name).join(', ')
    : 'a friendly opponent'
  return <main className="page-content game-play-page">
    <div className="game-play-actions"><Link className="text-link game-play-back" to="/games"><ArrowLeft size={17} /> Back to games</Link><button className="button button--small button--danger" type="button" disabled={ending} onClick={() => void endSession()}>{ending ? 'Ending…' : 'End session'}</button></div>
    <section className="game-play-header"><div><span className="eyebrow">Friendly match · {title}</span><h1>{isTrivia ? 'Think fast. Stay curious.' : 'Play at your own pace'}</h1><p>{isTrivia ? 'Five bright questions, kind competition, and something new to learn.' : 'Kind competition, clear rules, and a little room to breathe.'}</p></div><div className="game-play-badge"><Sparkle size={22} /> {isTrivia ? '15 seconds per question' : `Playing with ${opponentLabel}`}</div></section>
    {error && <p className="form-error" role="alert">{error}</p>}
    {match?.game !== 'ludo' && match?.game !== 'dominoes' && match?.game !== 'trivia' && state?.winner !== null && state?.winner !== undefined && <div className="game-result"><Trophy size={22} /> {state.winner === seat ? 'You won this round!' : `${players[state.winner]?.name ?? 'Your opponent'} won this round.`}</div>}
    {match?.game === 'ludo' && <LudoGame state={(state ?? {}) as Partial<LudoState>} send={send} playerIndex={viewerSeat.current} />}
    {match?.game === 'dominoes' && <DominoGame state={(state ?? {}) as Partial<DominoState>} send={send} error={error} playerIndex={viewerSeat.current} />}
    {match?.game === 'bingo' && <BingoBoard state={state ?? {}} send={send} />}
    {match?.game === 'trivia' && <TriviaGame state={(state ?? {}) as Partial<TriviaState>} send={send} error={error} playerIndex={viewerSeat.current} />}
    {match?.game === 'scribble' && <ScribbleGame state={(state ?? {}) as Partial<ScribbleState>} send={send} error={error} />}
  </main>
}

function BingoBoard({ state, send }: { state: Record<string, any>; send: (action: Record<string, unknown>) => void }) {
  const finished = state.winner !== null && state.winner !== undefined || state.draw
  return <section className="mini-game-card"><div className="bingo-head"><span>Drawn: {state.drawn?.length ?? 0}/75</span><button className="button button--primary button--small" type="button" disabled={finished} onClick={() => send({ action: 'draw' })}>Draw ball</button><button className="button button--secondary button--small" type="button" disabled={finished} onClick={() => send({ action: 'claim' })}>Claim Bingo</button></div><div className="bingo-card">{state.card?.flatMap((row: Array<number>, rowIndex: number) => row.map((number: number, colIndex: number) => <span className={state.marked?.[rowIndex]?.[colIndex] ? 'bingo-cell bingo-cell--marked' : 'bingo-cell'} key={`${rowIndex}-${colIndex}`}>{number || 'FREE'}</span>))}</div>{finished && <div className="game-result-actions"><strong>{state.draw ? 'The round ended in a draw.' : state.winner === Number(state.seat_index ?? 0) ? 'Bingo! You won.' : 'Bingo claimed.'}</strong><button className="button button--small button--primary game-play-again" type="button" onClick={() => send({ action: 'play_again' })}>Play again</button></div>}</section>
}
