import { useEffect, useRef, useState } from 'react'
import type { FormEvent, PointerEvent } from 'react'
import { Eraser, Pencil, Robot, Timer, Trophy } from '@phosphor-icons/react'

import { playerDisplayName } from '../lib/game-player'

type ScribblePlayer = { name: string; is_bot: boolean }
type ScribblePoint = { x: number; y: number }
type ScribbleStroke = { points: Array<ScribblePoint>; color: string; size: number; erase?: boolean }

export type ScribbleState = {
  seat_index?: number
  game: 'scribble'
  phase: 'choosing' | 'drawing' | 'guessing' | 'round_result' | 'finished'
  round: number
  rounds: number
  players: Array<ScribblePlayer>
  current_drawer: number
  drawer_name: string
  is_drawer: boolean
  word: string
  word_choices: Array<string>
  hint: string
  strokes: Array<ScribbleStroke>
  live_stroke?: ScribbleStroke | null
  guesses: Array<{ player: number; text: string; correct: boolean; warm?: boolean }>
  scores: Array<number>
  winner: number | null
  draw: boolean
  last_event: string
  guess_deadline: number | null
  round_points: Array<number>
  action_count?: number
}

type ScribbleGameProps = { state: Partial<ScribbleState>; send: (action: Record<string, unknown>) => void; error?: string }

const COLORS = ['#1f2421', '#315542', '#d87958', '#6c65a7', '#e1a93b', '#2f80ed', '#d94f70', '#19a974', '#8b5cf6']

export function ScribbleGame({ state, send, error = '' }: ScribbleGameProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null)
  const drawingRef = useRef<Array<ScribblePoint>>([])
  const livePointRef = useRef<ScribblePoint | null>(null)
  const drawnStrokeKeysRef = useRef(new Set<string>())
  const timeoutSentRef = useRef<number | null>(null)
  const [color, setColor] = useState(COLORS[0])
  const [tool, setTool] = useState<'pencil' | 'eraser'>('pencil')
  const [guess, setGuess] = useState('')
  const players = state.players ?? [{ name: 'You', is_bot: false }, { name: 'Milo Bot', is_bot: true }]
  const playerIndex = Number(state.seat_index ?? 0)
  const strokes = state.strokes ?? []
  const isDrawer = Boolean(state.is_drawer)
  const roundResult = state.phase === 'round_result'
  const finished = state.phase === 'finished' || state.winner !== null || state.draw
  const [secondsLeft, setSecondsLeft] = useState(30)

  const strokeKey = (stroke: ScribbleStroke) => `${stroke.erase ? 'erase' : 'draw'}:${stroke.color}:${stroke.size}:${stroke.points.map((point) => `${point.x},${point.y}`).join(';')}`
  const paintStroke = (context: CanvasRenderingContext2D, stroke: ScribbleStroke, width: number, height: number) => {
    if (stroke.points.length < 2) return
    context.globalCompositeOperation = stroke.erase ? 'destination-out' : 'source-over'
    context.strokeStyle = stroke.color
    context.lineWidth = stroke.size
    context.lineCap = 'round'
    context.lineJoin = 'round'
    context.beginPath()
    stroke.points.forEach((point, index) => {
      const x = point.x * width
      const y = point.y * height
      if (index === 0) context.moveTo(x, y)
      else context.lineTo(x, y)
    })
    context.stroke()
    context.globalCompositeOperation = 'source-over'
  }

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ratio = window.devicePixelRatio || 1
    const width = canvas.clientWidth
    const height = canvas.clientHeight
    canvas.width = width * ratio
    canvas.height = height * ratio
    const context = canvas.getContext('2d')
    if (!context) return
    context.scale(ratio, ratio)
    context.clearRect(0, 0, width, height)
    drawnStrokeKeysRef.current.clear()
    for (const stroke of strokes) {
      paintStroke(context, stroke, width, height)
      drawnStrokeKeysRef.current.add(strokeKey(stroke))
    }
  }, [state.round])

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas || !strokes.length) {
      if (!strokes.length && drawnStrokeKeysRef.current.size) {
        const context = canvas?.getContext('2d')
        if (context) context.clearRect(0, 0, canvas.clientWidth, canvas.clientHeight)
        drawnStrokeKeysRef.current.clear()
      }
      return
    }
    const context = canvas.getContext('2d')
    if (!context) return
    for (const stroke of strokes) {
      const key = strokeKey(stroke)
      if (drawnStrokeKeysRef.current.has(key)) continue
      paintStroke(context, stroke, canvas.clientWidth, canvas.clientHeight)
      drawnStrokeKeysRef.current.add(key)
    }
  }, [strokes])

  useEffect(() => {
    const canvas = canvasRef.current
    const stroke = state.live_stroke
    if (!canvas || !stroke) return
    const key = strokeKey(stroke)
    if (drawnStrokeKeysRef.current.has(key)) return
    const context = canvas.getContext('2d')
    if (!context) return
    paintStroke(context, stroke, canvas.clientWidth, canvas.clientHeight)
    drawnStrokeKeysRef.current.add(key)
  }, [state.live_stroke])

  useEffect(() => {
    if (state.phase !== 'guessing' || !state.guess_deadline) {
      setSecondsLeft(30)
      return
    }
    const update = () => setSecondsLeft(Math.max(0, Math.ceil((Number(state.guess_deadline) * 1000 - Date.now()) / 1000)))
    update()
    const timer = window.setInterval(update, 250)
    return () => window.clearInterval(timer)
  }, [state.phase, state.guess_deadline, state.action_count])

  useEffect(() => {
    if (state.phase !== 'guessing' || secondsLeft !== 0 || timeoutSentRef.current === state.action_count) return
    timeoutSentRef.current = state.action_count ?? 0
    send({ action: 'timeout' })
  }, [secondsLeft, state.phase, state.action_count, send])

  useEffect(() => {
    if (state.phase !== 'guessing' || isDrawer) return
    const ticker = window.setInterval(() => send({ action: 'hint_tick' }), 1000)
    return () => window.clearInterval(ticker)
  }, [state.phase, isDrawer, send])

  const pointFromEvent = (event: PointerEvent<HTMLCanvasElement>): ScribblePoint => {
    const bounds = event.currentTarget.getBoundingClientRect()
    return { x: Math.max(0, Math.min(1, (event.clientX - bounds.left) / bounds.width)), y: Math.max(0, Math.min(1, (event.clientY - bounds.top) / bounds.height)) }
  }
  const startDrawing = (event: PointerEvent<HTMLCanvasElement>) => {
    if (!isDrawer || state.phase !== 'drawing' || finished || roundResult) return
    event.currentTarget.setPointerCapture(event.pointerId)
    const point = pointFromEvent(event)
    drawingRef.current = [point]
    livePointRef.current = point
  }
  const continueDrawing = (event: PointerEvent<HTMLCanvasElement>) => {
    if (!drawingRef.current.length) return
    const point = pointFromEvent(event)
    const previous = livePointRef.current ?? point
    const canvas = event.currentTarget
    const context = canvas.getContext('2d')
    if (context) {
      paintStroke(context, { points: [previous, point], color, size: tool === 'eraser' ? 24 : 6, erase: tool === 'eraser' }, canvas.clientWidth, canvas.clientHeight)
    }
    drawingRef.current.push(point)
    livePointRef.current = point
    const stroke = { points: [previous, point], color, size: tool === 'eraser' ? 24 : 6, erase: tool === 'eraser' }
    drawnStrokeKeysRef.current.add(strokeKey(stroke))
    send({ action: 'stroke_segment', ...stroke })
  }
  const finishDrawing = () => {
    const points = drawingRef.current
    drawingRef.current = []
    livePointRef.current = null
    if (points.length === 1) {
      const stroke = { points: [points[0], points[0]], color, size: tool === 'eraser' ? 24 : 6, erase: tool === 'eraser' }
      send({ action: 'stroke_segment', ...stroke })
    }
  }
  const submitGuess = (event: FormEvent) => {
    event.preventDefault()
    if (!guess.trim() || isDrawer || state.phase !== 'guessing' || finished) return
    send({ action: 'guess', text: guess.trim() })
    setGuess('')
  }

  return <section className="scribble-game-shell" aria-label="Scribble drawing and guessing game">
    <header className="scribble-game-head">
      <div><span className="eyebrow">Scribble · Round {state.round ?? 1} of {state.rounds ?? 6}</span><h2>{finished ? 'What a lovely game!' : roundResult ? 'Round complete!' : isDrawer ? state.phase === 'choosing' ? 'Choose a word to draw.' : 'Draw a clue for your friends.' : `${state.drawer_name ?? 'Your friend'} is drawing…`}</h2><p aria-live="polite">{isDrawer && state.word ? <>Your secret word: <strong>{state.word}</strong></> : state.last_event ?? 'Look closely, then make your best guess.'}</p></div>
      <div className="scribble-prompt"><Pencil size={22} weight="fill" /><span>{isDrawer && state.phase === 'choosing' ? 'Pick one below' : isDrawer ? 'Keep it secret' : state.hint ?? '_ _ _ _ _'}</span></div>
    </header>

    <div className="scribble-scoreboard" aria-label="Scores">
      {players.map((player, index) => <div className={index === state.current_drawer && !finished ? 'scribble-score scribble-score--active' : 'scribble-score'} key={player.name}><span className="scribble-score__avatar">{player.is_bot ? <Robot size={17} weight="fill" /> : <Pencil size={17} weight="fill" />}</span><span>{playerDisplayName(player.name, index, playerIndex)}</span><strong>{state.scores?.[index] ?? 0}</strong></div>)}
    </div>

    {state.phase === 'guessing' && <div className={`scribble-timer${secondsLeft <= 7 ? ' scribble-timer--urgent' : ''}`} role="timer"><Timer size={18} weight="fill" /><strong>{secondsLeft}s to guess</strong><span><i style={{ width: `${Math.max(0, Math.min(100, (secondsLeft / 30) * 100))}%` }} /></span></div>}
    <div className="scribble-canvas-wrap"><canvas ref={canvasRef} className={isDrawer && state.phase === 'drawing' ? 'scribble-canvas scribble-canvas--draw' : 'scribble-canvas'} onPointerDown={startDrawing} onPointerMove={continueDrawing} onPointerUp={finishDrawing} onPointerCancel={finishDrawing} aria-label={isDrawer ? 'Drawing canvas' : 'Shared drawing'} /><span className="scribble-canvas-note">{isDrawer && state.phase === 'drawing' ? 'Draw with your finger or mouse' : 'Watch the sketch and guess below'}</span></div>

    <div className="scribble-controls">
      {isDrawer && state.phase === 'choosing' && !finished && <div className="scribble-word-choices" aria-label="Choose a word">{(state.word_choices ?? []).map((word) => <button className="button button--secondary button--small" type="button" key={word} onClick={() => send({ action: 'choose_word', word })}>{word}</button>)}</div>}
      {isDrawer && state.phase === 'drawing' && !finished && <><div className="scribble-palette" aria-label="Drawing colors">{COLORS.map((item) => <button aria-label={`Use ${item}`} className={color === item && tool === 'pencil' ? 'scribble-color scribble-color--selected' : 'scribble-color'} style={{ backgroundColor: item }} key={item} type="button" onClick={() => { setColor(item); setTool('pencil') }} />)}</div><button className={tool === 'eraser' ? 'button button--primary button--small' : 'button button--secondary button--small'} type="button" onClick={() => setTool('eraser')} aria-pressed={tool === 'eraser'}><Eraser size={17} /> Eraser</button><button className="button button--secondary button--small" type="button" onClick={() => { const canvas = canvasRef.current; const context = canvas?.getContext('2d'); if (canvas && context) context.clearRect(0, 0, canvas.clientWidth, canvas.clientHeight); drawnStrokeKeysRef.current.clear(); send({ action: 'clear' }) }}><Eraser size={17} /> Clear all</button><button className="button button--primary button--small" type="button" onClick={() => send({ action: 'end_turn' })}>Finish drawing</button></>}
      {!isDrawer && state.phase === 'guessing' && !finished && <form className="scribble-guess-form" onSubmit={submitGuess}><label htmlFor="scribble-guess">Your guess</label><input id="scribble-guess" value={guess} onChange={(event) => setGuess(event.target.value)} placeholder="I think it is…" maxLength={80} /><button className="button button--primary button--small" type="submit">Guess</button></form>}
    </div>
    {error && <p className="form-error" role="alert">{error}</p>}
    {!!state.guesses?.length && <div className="scribble-guesses" aria-live="polite">{state.guesses.slice(-4).map((item, index) => <span className={item.correct ? 'scribble-guess scribble-guess--correct' : item.warm ? 'scribble-guess scribble-guess--warm' : 'scribble-guess'} key={`${item.text}-${index}`}>{players[item.player]?.name}: {item.text}{item.correct ? ' ✓' : item.warm ? ' · Warm' : ''}</span>)}</div>}
    {roundResult && <div className="scribble-round-result" role="dialog" aria-labelledby="scribble-round-title"><div><Trophy size={28} weight="fill" /><p className="eyebrow">Round {state.round ?? 1} result</p><h3 id="scribble-round-title">{state.last_event}</h3></div><div className="scribble-round-scores">{players.map((player, index) => <div key={player.name}><span>{player.name}</span><strong>+{state.round_points?.[index] ?? 0}</strong><small>{state.scores?.[index] ?? 0} total</small></div>)}</div><button className="button button--primary" type="button" onClick={() => send({ action: 'continue' })}>Continue</button></div>}
    {finished && <div className="scribble-result" role="status"><Trophy size={25} weight="fill" /><span>{state.draw ? 'A shared tie!' : players[state.winner ?? 0]?.name + ' wins the game!'}</span><button className="button button--primary button--small game-play-again" type="button" onClick={() => send({ action: 'play_again' })}>Play again</button></div>}
    <details className="scribble-rules"><summary>How Scribble works</summary><p>One player gets a secret word and draws it. Everyone else guesses. Correct guesses earn 100 points, the drawer earns 50, and the player with the highest score after six rounds wins.</p></details>
  </section>
}
