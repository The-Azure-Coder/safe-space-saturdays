import { lazy, Suspense, useEffect, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { createFileRoute, Link, useParams } from '@tanstack/react-router'
import { ArrowLeft, Eye, Sparkle, Trophy } from '@phosphor-icons/react'

import { LudoGame } from '../components/ludo-game'
import type { LudoState } from '../components/ludo-game'
import { DominoGame } from '../components/domino-game'
import type { DominoState } from '../components/domino-game'
import { TriviaGame } from '../components/trivia-game'
import type { TriviaState } from '../components/trivia-game'
import { ScribbleGame } from '../components/scribble-game'
import { CheckersGame } from '../components/checkers-game'
const TogetherGame = lazy(() => import('../components/together-game').then((module) => ({ default: module.TogetherGame })))
import { GameRoomControls } from '../components/game-room-controls'
import { GeneralLoader } from '../components/general-loader'
import type { ScribbleState } from '../components/scribble-game'
import { API_URL, api, apiRetryDelay, shouldRetryApiRequest } from '../lib/api'
import type { GameSession } from '../lib/api'

export const Route = createFileRoute('/games/session/$matchId')({ component: GameSessionScreen })

function GameSessionScreen() {
  const { matchId } = useParams({ from: '/games/session/$matchId' })
  const [match, setMatch] = useState<GameSession | null>(null)
  const viewerSeat = useRef(0)
  const [error, setError] = useState('')
  const [ending, setEnding] = useState(false)
  const socket = useRef<WebSocket | null>(null)
  const gameSession = useQuery({
    queryKey: ['game-session', matchId],
    queryFn: () => api.gameSession(matchId),
    retry: shouldRetryApiRequest,
    retryDelay: apiRetryDelay,
  })

  useEffect(() => {
    if (!gameSession.data) return
    viewerSeat.current = Number(gameSession.data.state.seat_index ?? 0)
    setMatch(gameSession.data)
    setError('')
  }, [gameSession.data])

  useEffect(() => {
    if (!gameSession.data) return
    const connection = new WebSocket(`${API_URL.replace(/^http/, 'ws')}/api/games/sessions/${matchId}/ws`)
    socket.current = connection
    connection.onmessage = (event) => {
      const message = JSON.parse(event.data) as { type: string; match?: GameSession; spectator_count?: number; detail?: string; segment?: ScribbleState['live_stroke']; state?: Record<string, any> }
      if (message.type === 'drawing_segment' && message.segment) {
        const segment = message.segment
        setMatch((current) => current ? { ...current, state: { ...current.state, live_stroke: segment } } : current)
      }
      if (message.type === 'state' && message.match) {
        const nextMatch = message.match
        nextMatch.spectator_count = message.spectator_count ?? nextMatch.spectator_count ?? 0
        if (nextMatch.state.seat_index === undefined) {
          nextMatch.state.seat_index = viewerSeat.current
        } else {
          viewerSeat.current = Number(nextMatch.state.seat_index)
        }
        setMatch(nextMatch)
      }
      if (message.type === 'together' && message.state) {
        setMatch((current) => current ? { ...current, state: { ...current.state, ...message.state } } : current)
      }
      if (message.type === 'spectator_count') setMatch((current) => current ? { ...current, spectator_count: message.spectator_count ?? 0 } : current)
      if (message.type === 'session_ended') window.location.href = '/games'
      if (message.type === 'game_changed') window.location.href = '/games'
      if (message.type === 'error') setError(message.detail ?? 'That action was not accepted')
    }
    connection.onerror = () => setError('Connection lost. Refresh to reconnect.')
    return () => connection.close()
  }, [gameSession.data, matchId])
  const send = (action: Record<string, unknown>) => {
    if (match?.spectator) return
    setError('')
    if (action.action === 'play_again') void api.gameAction(matchId, action).then(setMatch).catch((reason: Error) => setError(reason.message))
    else if (socket.current?.readyState === WebSocket.OPEN) socket.current.send(JSON.stringify({ type: 'action', action }))
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
  const isSpectator = Boolean(match?.spectator)
  if (!match && gameSession.isPending)
    return <main className="page-content game-play-page"><GeneralLoader label="Loading your game…" /></main>
  if (!match && gameSession.isError)
    return <main className="page-content game-play-page"><GeneralLoader label="Reconnecting to your game…" onRetry={() => void gameSession.refetch()} /></main>
  const title = match?.game === 'together' ? 'Together' : match?.game === 'ludo' ? 'Ludo' : match?.game === 'dominoes' ? 'Block Dominoes' : match?.game === 'bingo' ? 'Bingo' : match?.game === 'scribble' ? 'Scribble' : match?.game === 'abc-fast-slow' ? 'ABC Fast or Slow' : match?.game === 'checkers' ? 'Checkers' : 'Trivia Battle'
  const isTrivia = match?.game === 'trivia'
  const players = state?.players ?? []
  const seat = Number(state?.seat_index ?? 0)
  const opponents = players.filter((_player: { name: string; is_bot: boolean }, index: number) => index !== seat)
  const opponentLabel = opponents.length
    ? opponents.map((player: { name: string; is_bot: boolean }) => player.name).join(', ')
    : 'a friendly opponent'
  return <main className="page-content game-play-page">
    <div className="game-play-actions"><Link className="text-link game-play-back" to="/games"><ArrowLeft size={17} /> Back to games</Link>{!isSpectator && <div className="game-play-actions__right"><GameRoomControls roomId={match?.room_id ?? 0} /><button className="button button--small button--danger" type="button" disabled={ending} onClick={() => void endSession()}>{ending ? 'Ending…' : 'End session'}</button></div>}</div>
    <section className="game-play-header"><div><span className="eyebrow">Friendly match · {title}</span><h1>{isTrivia ? 'Think fast. Stay curious.' : 'Play at your own pace'}</h1><p>{isTrivia ? 'Five bright questions, kind competition, and something new to learn.' : 'Kind competition, clear rules, and a little room to breathe.'}</p></div><div className="game-play-badge"><Sparkle size={22} /> {isTrivia ? '15 seconds per question' : `Playing with ${opponentLabel}`}{(match?.spectator_count ?? 0) > 0 && <span className="spectator-count" aria-label={`${match?.spectator_count} people watching`}><Eye size={17} aria-hidden="true" /> {match?.spectator_count}</span>}</div></section>
    {isSpectator && <p className="spectator-banner" role="status"><Eye size={18} aria-hidden="true" /> You are spectating this live game. The game is read-only.</p>}
    {error && <p className="form-error" role="alert">{error}</p>}
    {match?.game !== 'ludo' && match?.game !== 'dominoes' && match?.game !== 'trivia' && state?.winner !== null && state?.winner !== undefined && <div className="game-result"><Trophy size={22} /> {isSpectator ? `${players[state.winner]?.name ?? 'A player'} won this round.` : state.winner === seat ? 'You won this round!' : `${players[state.winner]?.name ?? 'Your opponent'} won this round.`}</div>}
    <div className="spectator-game-view" inert={isSpectator || undefined}>
      {match?.game === 'ludo' && <LudoGame state={(state ?? {}) as Partial<LudoState>} send={send} playerIndex={isSpectator ? 0 : viewerSeat.current} />}
      {match?.game === 'dominoes' && <DominoGame state={(state ?? {}) as Partial<DominoState>} send={send} error={error} playerIndex={isSpectator ? 0 : viewerSeat.current} />}
      {match?.game === 'bingo' && <BingoBoard state={state ?? {}} send={send} />}
      {match?.game === 'trivia' && <TriviaGame state={(state ?? {}) as Partial<TriviaState>} send={send} error={error} playerIndex={isSpectator ? 0 : viewerSeat.current} />}
      {match?.game === 'scribble' && <ScribbleGame state={(state ?? {}) as Partial<ScribbleState>} send={send} error={error} />}
      {match?.game === 'abc-fast-slow' && <AbcFastSlowGame state={state ?? {}} send={send} />}
      {match?.game === 'checkers' && <CheckersGame state={(state ?? {}) as any} send={send} />}
      {match?.game === 'together' && <Suspense fallback={<GeneralLoader label="Loading Together…" />}><TogetherGame state={(state ?? {}) as any} send={send} spectator={isSpectator} /></Suspense>}
    </div>
  </main>
}

function AbcFastSlowGame({ state, send }: { state: Record<string, any>; send: (action: Record<string, unknown>) => void }) {
  const [answers, setAnswers] = useState<Record<string, string>>({})
  const [now, setNow] = useState(() => Date.now() / 1000)
  const timeoutSent = useRef(false)
  const [votedKeys, setVotedKeys] = useState<Set<string>>(new Set())
  const pickerTimer = useRef<number | null>(null)
  const [pickerSpeed, setPickerSpeed] = useState<'fast' | 'slow'>('slow')
  const [pickerIndex, setPickerIndex] = useState(0)
  const [pickerRunning, setPickerRunning] = useState(false)
  useEffect(() => setAnswers({}), [state.round, state.letter])
  useEffect(() => setVotedKeys(new Set()), [state.round, state.letter, state.phase])
  useEffect(() => {
    setPickerSpeed('slow')
    setPickerIndex(0)
    setPickerRunning(false)
    if (pickerTimer.current !== null) window.clearInterval(pickerTimer.current)
  }, [state.round])
  useEffect(() => () => {
    if (pickerTimer.current !== null) window.clearInterval(pickerTimer.current)
  }, [])
  useEffect(() => {
    if (state.phase === 'answering' && pickerTimer.current !== null) {
      window.clearInterval(pickerTimer.current)
      pickerTimer.current = null
      setPickerRunning(false)
    }
  }, [state.phase])
  // The picker animation is driven by the shared server phase, so every
  // connected player sees the wheel spinning as soon as the chooser starts it.
  useEffect(() => {
    if (pickerTimer.current !== null) window.clearInterval(pickerTimer.current)
    pickerTimer.current = null
    if (state.phase !== 'letter_picker_running') {
      setPickerRunning(false)
      return
    }
    const speed = state.picker_speed === 'fast' ? 'fast' : 'slow'
    setPickerSpeed(speed)
    setPickerRunning(true)
    pickerTimer.current = window.setInterval(() => {
      setPickerIndex((current) => (current + 1) % 26)
    }, speed === 'fast' ? 80 : 280)
    return () => {
      if (pickerTimer.current !== null) window.clearInterval(pickerTimer.current)
      pickerTimer.current = null
    }
  }, [state.phase, state.picker_speed])
  useEffect(() => {
    timeoutSent.current = false
    if (state.phase !== 'answering' || !state.deadline) return
    const timer = window.setInterval(() => {
      const current = Date.now() / 1000
      setNow(current)
      if (current >= Number(state.deadline) && !state.submitted?.[Number(state.seat_index ?? 0)] && !timeoutSent.current) {
        timeoutSent.current = true
        send({ action: 'timeout' })
      }
    }, 250)
    return () => window.clearInterval(timer)
  }, [state.phase, state.deadline, state.seat_index, state.submitted, send])
  const categories = state.categories ?? ['Animal', 'Place', 'Food', 'Thing']
  const seat = Number(state.seat_index ?? 0)
  const dictator = Number(state.dictator_player ?? state.letter_chooser ?? -1)
  const dictatorName = state.players?.[dictator]?.name ?? 'A random player'
  const finished = state.phase === 'complete'
  const pickerPhase = state.phase === 'letter_picker' || state.phase === 'letter_picker_running'
  const pickerLetter = state.letter ?? 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'[pickerIndex]
  const startPicker = (speed: 'fast' | 'slow') => {
    if (pickerRunning) return
    setPickerSpeed(speed)
    setPickerIndex(0)
    send({ action: 'start_picker', speed })
  }
  const stopPicker = () => {
    if (!pickerRunning) return
    send({ action: 'stop_picker' })
  }
  const voted = state.votes?.[seat] ?? {}
  const voteCount = new Set([...Object.keys(voted), ...votedKeys]).size
  const requiredVotes = Math.max(1, (state.player_count ?? 2) - 1) * categories.length
  return <section className="mini-game-card abc-game" aria-label="ABC Fast or Slow game">
    <div className="abc-game__hero"><div><span className="eyebrow">Round {state.round ?? 1} of {state.rounds ?? 3} · {state.phase === 'voting' ? 'Review answers' : state.phase === 'answering' ? 'Fast round' : pickerPhase ? 'Pick the letter' : 'Round result'}</span><h2>{state.letter ? `Letter ${state.letter}` : 'Pick a letter'}</h2><p>{state.last_event ?? 'Think fast, but make your answer count.'}</p><div className="abc-game__round-meta" aria-label={`Dictator and letter chooser: ${dictatorName}`}>Dictator / letter chooser: <strong>{dictatorName}</strong><span>·</span><span>Letter chosen by the wheel</span></div>{state.phase === 'answering' && state.deadline && <small className="abc-game__timer">Time left: {Math.max(0, Math.ceil(Number(state.deadline) - now))}s</small>}</div><div className="abc-game__letter" aria-hidden="true">{state.letter ?? '?'}</div></div>
    <div className="abc-game__scoreboard">{(state.players ?? []).map((player: { name: string }, index: number) => <span className={index === dictator ? 'abc-game__player abc-game__player--dictator' : 'abc-game__player'} key={`${player.name}-${index}`}><strong>{player.name}</strong>{index === dictator && <small>Chooser</small>} {state.scores?.[index] ?? 0} pts</span>)}</div>
    {pickerPhase ? <div className="abc-game__picker" aria-label="Letter picker">
      <p className="eyebrow">Choose a pace, then stop the wheel</p>
      <div className={`abc-game__picker-letter ${pickerRunning ? 'is-spinning' : ''}`} aria-live="polite">{pickerLetter}</div>
      <div className="abc-game__picker-speeds" role="group" aria-label="Letter picker speed">
        <button className={pickerSpeed === 'slow' ? 'button button--primary' : 'button button--secondary'} type="button" aria-pressed={pickerSpeed === 'slow'} disabled={pickerRunning} onClick={() => setPickerSpeed('slow')}>Slow</button>
        <button className={pickerSpeed === 'fast' ? 'button button--primary' : 'button button--secondary'} type="button" aria-pressed={pickerSpeed === 'fast'} disabled={pickerRunning} onClick={() => setPickerSpeed('fast')}>Fast</button>
      </div>
      {!pickerRunning ? <button className="button button--primary" type="button" onClick={() => startPicker(pickerSpeed)}>Start {pickerSpeed} letter picker</button> : <button className="button button--primary" type="button" onClick={stopPicker}>Stop on this letter</button>}
    </div> : state.phase === 'answering' ? <form className="abc-game__form" onSubmit={(event) => { event.preventDefault(); send({ action: 'submit', answers }) }}>
      {categories.map((category: string) => <label key={category}>{category}<input value={answers[category] ?? ''} onChange={(event) => setAnswers((current) => ({ ...current, [category]: event.target.value }))} placeholder={`${state.letter ?? ''}…`} /></label>)}
      <div className="abc-game__form-actions"><button className="button button--primary" type="submit" disabled={state.submitted?.[seat]}>Submit answers</button><button className="button button--secondary" type="button" disabled={state.submitted?.[seat]} onClick={() => send({ action: 'submit', answers: {} })}>Submit blank</button></div>
    </form> : state.phase === 'voting' ? <div className="abc-game__review"><div className="abc-game__review-progress">Your review: {voteCount}/{requiredVotes}</div>{(state.answers ?? []).map((playerAnswers: Record<string, string>, target: number) => <article className="abc-game__answer-card" key={target}><strong>{state.players?.[target]?.name ?? `Player ${target + 1}`}</strong>{target === seat ? <p className="abc-game__own-answer">Your answers are being checked by the other players.</p> : categories.map((category: string) => { const key = `${target}:${category}`; const value = playerAnswers[category] ?? ''; const alreadyVoted = key in voted || votedKeys.has(key); const recordVote = (valid: boolean) => { setVotedKeys((current) => new Set(current).add(key)); send({ action: 'vote', target, category, valid }) }; return <div className="abc-game__answer-row" key={key}><span><small>{category}</small>{value || 'No answer'}</span><button type="button" aria-label={`Mark ${state.players?.[target]?.name ?? 'answer'} ${category} valid`} className="button button--small button--primary" disabled={alreadyVoted} onClick={() => recordVote(true)}>Valid</button><button type="button" aria-label={`Mark ${state.players?.[target]?.name ?? 'answer'} ${category} invalid`} className="button button--small button--secondary" disabled={alreadyVoted} onClick={() => recordVote(false)}>Skip</button></div> })}</article>)}</div> : <div className="abc-game__result" aria-live="polite"><h3>{finished ? (state.draw ? 'A tie — beautifully played.' : state.winner === seat ? 'You won the word race!' : `${state.players?.[state.winner]?.name ?? 'Your opponent'} wins!`) : 'Round complete'}</h3><p>{state.last_event}</p>{finished ? <button className="button button--primary" type="button" onClick={() => send({ action: 'play_again' })}>Play again</button> : <button className="button button--primary" type="button" onClick={() => send({ action: 'next_round' })}>Next round</button>}</div>}
  </section>
}

function BingoBoard({ state, send }: { state: Record<string, any>; send: (action: Record<string, unknown>) => void }) {
  const finished = state.winner !== null && state.winner !== undefined || state.draw
  return <section className="mini-game-card"><div className="bingo-head"><span>Drawn: {state.drawn?.length ?? 0}/75</span><button className="button button--primary button--small" type="button" disabled={finished} onClick={() => send({ action: 'draw' })}>Draw ball</button><button className="button button--secondary button--small" type="button" disabled={finished} onClick={() => send({ action: 'claim' })}>Claim Bingo</button></div><div className="bingo-card">{state.card?.flatMap((row: Array<number>, rowIndex: number) => row.map((number: number, colIndex: number) => <span className={state.marked?.[rowIndex]?.[colIndex] ? 'bingo-cell bingo-cell--marked' : 'bingo-cell'} key={`${rowIndex}-${colIndex}`}>{number || 'FREE'}</span>))}</div>{finished && <div className="game-result-actions"><strong>{state.draw ? 'The round ended in a draw.' : state.winner === Number(state.seat_index ?? 0) ? 'Bingo! You won.' : 'Bingo claimed.'}</strong><button className="button button--small button--primary game-play-again" type="button" onClick={() => send({ action: 'play_again' })}>Play again</button></div>}</section>
}
