import { useEffect, useRef, useState } from 'react'
import { CheckCircle, Clock, Fire, Robot, SpeakerHigh, SpeakerSlash, Sparkle, Trophy, UserCircle, XCircle } from '@phosphor-icons/react'

import { playerDisplayName } from '../lib/game-player'

type TriviaPlayer = { name: string; is_bot: boolean }

export type TriviaState = {
  current_player: number
  winner: number | null
  draw: boolean
  phase: 'board' | 'question' | 'bot' | 'reveal' | 'complete'
  question_index: number
  question_count: number
  question: string
  category: string | null
  value: number | null
  board?: Array<{ category: string; values: Array<number> }>
  used_clues?: Array<string>
  point_values?: Array<number>
  options: Array<string>
  scores: Array<number>
  streaks: Array<number>
  selected_answers: Array<number | null>
  answer_points: Array<number>
  correct_answer?: number
  deadline: number
  action_count: number
  last_event: string
  players: Array<TriviaPlayer>
}

const DEFAULT_PLAYERS: Array<TriviaPlayer> = [
  { name: 'You', is_bot: false },
  { name: 'Milo Bot', is_bot: true },
]

function playTone(kind: 'tap' | 'correct' | 'wrong' | 'complete') {
  const context = new AudioContext()
  const notes = kind === 'correct' ? [523, 659, 784] : kind === 'complete' ? [392, 523, 659, 784] : kind === 'wrong' ? [220, 185] : [440]
  notes.forEach((frequency, index) => {
    const oscillator = context.createOscillator()
    const gain = context.createGain()
    const start = context.currentTime + index * 0.1
    oscillator.type = kind === 'wrong' ? 'triangle' : 'sine'
    oscillator.frequency.value = frequency
    gain.gain.setValueAtTime(0.0001, start)
    gain.gain.exponentialRampToValueAtTime(0.08, start + 0.015)
    gain.gain.exponentialRampToValueAtTime(0.0001, start + 0.16)
    oscillator.connect(gain).connect(context.destination)
    oscillator.start(start)
    oscillator.stop(start + 0.18)
  })
  window.setTimeout(() => void context.close(), notes.length * 120 + 240)
}

export function TriviaGame({ state, send, error, playerIndex = 0 }: { state: Partial<TriviaState>; send: (action: Record<string, unknown>) => void; error?: string; playerIndex?: number }) {
  const players = state.players?.length === 2 ? state.players : DEFAULT_PLAYERS
  const thinkingPlayer = players[state.current_player ?? 1]?.name ?? 'Your opponent'
  const phase = state.phase ?? 'question'
  const questionIndex = state.question_index ?? 0
  const questionCount = state.question_count ?? 15
  const scores = state.scores ?? [0, 0]
  const streaks = state.streaks ?? [0, 0]
  const selectedAnswers = state.selected_answers ?? [null, null]
  const answerPoints = state.answer_points ?? [0, 0]
  const [secondsLeft, setSecondsLeft] = useState(15)
  const [pending, setPending] = useState(false)
  const [soundOn, setSoundOn] = useState(false)
  const timedOutQuestion = useRef<number | null>(null)
  const priorPhase = useRef(phase)

  useEffect(() => {
    setPending(false)
    timedOutQuestion.current = null
  }, [questionIndex, state.action_count, error])

  useEffect(() => {
    if (phase !== 'question') return
    const update = () => setSecondsLeft(Math.max(0, Math.ceil((Number(state.deadline ?? Date.now() / 1000 + 15) * 1000 - Date.now()) / 1000)))
    update()
    const timer = window.setInterval(update, 250)
    return () => window.clearInterval(timer)
  }, [phase, questionIndex, state.deadline])

  useEffect(() => {
    if (phase === 'question' && secondsLeft === 0 && timedOutQuestion.current !== questionIndex && !pending) {
      timedOutQuestion.current = questionIndex
      setPending(true)
      send({ answer: -1, response_ms: 15_000 })
    }
  }, [phase, secondsLeft, questionIndex, pending, send])

  useEffect(() => {
    if (!soundOn || priorPhase.current === phase) {
      priorPhase.current = phase
      return
    }
    if (phase === 'reveal') playTone(selectedAnswers[playerIndex] === state.correct_answer ? 'correct' : 'wrong')
    if (phase === 'complete') playTone('complete')
    priorPhase.current = phase
  }, [phase, selectedAnswers, soundOn, state.correct_answer])

  const answer = (index: number) => {
    if (phase !== 'question' || pending) return
    setPending(true)
    if (soundOn) playTone('tap')
    send({ answer: index, response_ms: Math.max(0, (15 - secondsLeft) * 1000) })
  }
  const isReveal = phase === 'reveal' || phase === 'complete'
  const progress = Math.min(100, (((state.used_clues?.length ?? questionIndex) + (isReveal ? 0 : 0)) / questionCount) * 100)
  const resultText = state.draw ? 'A perfect tie!' : state.winner === playerIndex ? 'You are the trivia star!' : state.winner !== undefined && state.winner !== null ? `${players[state.winner]?.name ?? 'Your opponent'} wins this round!` : ''

  return <section className="trivia-game-shell" aria-label="Trivia arena">
    <div className="trivia-topline">
      <div><span className="eyebrow">{phase === 'board' ? 'Jeopardy board' : `Clue ${questionIndex} of ${questionCount}`}</span><strong>{state.category ?? 'Choose your category'}</strong></div>
      <button className="trivia-sound" type="button" aria-pressed={soundOn} aria-label={soundOn ? 'Mute game sounds' : 'Turn on game sounds'} onClick={() => { setSoundOn((value) => !value); if (!soundOn) playTone('tap') }}>
        {soundOn ? <SpeakerHigh size={19} weight="fill" /> : <SpeakerSlash size={19} />}<span>{soundOn ? 'Sound on' : 'Sound off'}</span>
      </button>
    </div>
    <div className="trivia-progress" aria-label={`${Math.round(progress)} percent complete`}><span style={{ width: `${progress}%` }} /></div>

    <div className="trivia-scoreboard">
      {players.map((player, index) => <article className={`trivia-player${index === playerIndex ? ' trivia-player--you' : ''}${state.current_player === index && !isReveal ? ' trivia-player--active' : ''}`} key={player.name}>
        <span className="trivia-player__avatar">{player.is_bot ? <Robot size={25} weight="fill" /> : <UserCircle size={26} weight="fill" />}</span>
        <span><small>{playerDisplayName(player.name, index, playerIndex)}</small><strong>{scores[index] ?? 0}</strong></span>
        {(streaks[index] ?? 0) > 1 && <em><Fire size={14} weight="fill" /> {streaks[index]} streak</em>}
      </article>)}
    </div>

    {phase === 'board' ? <TriviaBoard state={state} playerIndex={playerIndex} send={send} players={players} /> : phase === 'complete' ? <div className="trivia-finale" aria-live="polite">
      <span><Trophy size={42} weight="fill" /></span><p className="eyebrow">Round complete</p><h2>{resultText}</h2><p>Final score: {scores[0] ?? 0} to {scores[1] ?? 0}. Every question was a chance to learn something new.</p><LinkToGames send={send} />
    </div> : <>
      <div className={`trivia-timer${secondsLeft <= 5 && phase === 'question' ? ' trivia-timer--urgent' : ''}`} aria-label={`${secondsLeft} seconds remaining`}>
        <Clock size={18} weight="fill" /><strong>{phase === 'question' ? `${secondsLeft}s` : phase === 'bot' ? `${thinkingPlayer} is choosing…` : 'Answer reveal'}</strong>
        {phase === 'question' && <span><i style={{ width: `${(secondsLeft / 15) * 100}%` }} /></span>}
      </div>
      <div className="trivia-question" key={`${state.category}-${state.value}`}><Sparkle size={22} weight="fill" /><span className="trivia-question__value">{state.value} points</span><h2>{state.question}</h2></div>
      <div className="trivia-options">
        {(state.options ?? []).map((option, index) => {
          const correct = isReveal && state.correct_answer === index
          const chosen = selectedAnswers[playerIndex] === index
          const wrong = isReveal && chosen && !correct
          return <button className={`trivia-option${correct ? ' trivia-option--correct' : ''}${wrong ? ' trivia-option--wrong' : ''}${chosen ? ' trivia-option--chosen' : ''}`} type="button" disabled={phase !== 'question' || state.current_player !== playerIndex || pending} onClick={() => answer(index)} key={option}>
            <span>{String.fromCharCode(65 + index)}</span><strong>{option}</strong>{correct && <CheckCircle size={22} weight="fill" />}{wrong && <XCircle size={22} weight="fill" />}
          </button>
        })}
      </div>
      <div className="trivia-feedback" aria-live="polite">
        {phase === 'bot' && <p><span className="trivia-thinking" aria-hidden="true"><i /><i /><i /></span> Answer locked. {thinkingPlayer} is thinking.</p>}
        {phase === 'reveal' && <div className={selectedAnswers[playerIndex] === state.correct_answer ? 'trivia-feedback__correct' : 'trivia-feedback__wrong'}>
          <span>{selectedAnswers[playerIndex] === state.correct_answer ? <CheckCircle size={25} weight="fill" /> : <Sparkle size={24} weight="fill" />}</span>
          <p><strong>{state.last_event}</strong>{answerPoints[playerIndex] > 0 ? ` +${answerPoints[playerIndex]} points` : ' No points this time — the next one is yours.'}</p>
          <button className="button button--primary button--small" type="button" onClick={() => send({ action: 'next' })}>{questionIndex >= questionCount ? 'See final scores' : 'Back to board'}</button>
        </div>}
      </div>
    </>}
  </section>
}

function TriviaBoard({ state, playerIndex, send, players }: { state: Partial<TriviaState>; playerIndex: number; send: (action: Record<string, unknown>) => void; players: Array<TriviaPlayer> }) {
  const activePlayer = state.current_player ?? 0
  const used = new Set(state.used_clues ?? [])
  return <div className="trivia-board-wrap">
    <div className="trivia-board-status"><Sparkle size={18} weight="fill" /><strong>{activePlayer === playerIndex ? 'Your turn — choose a clue' : `${players[activePlayer]?.name ?? 'Your opponent'} is choosing…`}</strong></div>
    <div className="trivia-board" aria-label="Trivia categories and point values">
      {(state.board ?? []).map((column) => <div className="trivia-board__column" key={column.category}>
        <h3>{column.category}</h3>
        {column.values.map((value) => {
          const key = `${column.category}:${value}`
          const claimed = used.has(key)
          return <button className="trivia-board__tile" type="button" disabled={claimed || activePlayer !== playerIndex} key={key} onClick={() => send({ action: 'select_clue', category: column.category, value })}>{claimed ? '✓' : `${value}`}</button>
        })}
      </div>)}
    </div>
    <p className="trivia-board-hint">Pick a category, choose your points, then both players answer the clue.</p>
  </div>
}

function LinkToGames({ send }: { send: (action: Record<string, unknown>) => void }) {
  return <button className="button button--primary" type="button" onClick={() => send({ action: 'play_again' })}>Play again</button>
}
