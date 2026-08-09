import { useEffect, useRef, useState } from 'react'
import type { FormEvent, PointerEvent } from 'react'
import { Eraser, Pencil, Robot, Trophy } from '@phosphor-icons/react'

type ScribblePlayer = { name: string; is_bot: boolean }
type ScribblePoint = { x: number; y: number }
type ScribbleStroke = { points: Array<ScribblePoint>; color: string; size: number }

export type ScribbleState = {
  game: 'scribble'
  phase: 'drawing' | 'guessing' | 'finished'
  round: number
  rounds: number
  players: Array<ScribblePlayer>
  current_drawer: number
  drawer_name: string
  is_drawer: boolean
  word: string
  hint: string
  strokes: Array<ScribbleStroke>
  guesses: Array<{ player: number; text: string; correct: boolean }>
  scores: Array<number>
  winner: number | null
  draw: boolean
  last_event: string
}

type ScribbleGameProps = { state: Partial<ScribbleState>; send: (action: Record<string, unknown>) => void; error?: string }

const COLORS = ['#315542', '#d87958', '#6c65a7', '#e1a93b']

export function ScribbleGame({ state, send, error = '' }: ScribbleGameProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null)
  const drawingRef = useRef<Array<ScribblePoint>>([])
  const [color, setColor] = useState(COLORS[0])
  const [guess, setGuess] = useState('')
  const players = state.players ?? [{ name: 'You', is_bot: false }, { name: 'Milo Bot', is_bot: true }]
  const strokes = state.strokes ?? []
  const isDrawer = Boolean(state.is_drawer)
  const finished = state.phase === 'finished' || state.winner !== null || state.draw

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
    context.lineCap = 'round'
    context.lineJoin = 'round'
    for (const stroke of strokes) {
      if (stroke.points.length < 2) continue
      context.strokeStyle = stroke.color
      context.lineWidth = stroke.size
      context.beginPath()
      stroke.points.forEach((point, index) => {
        const x = point.x * width
        const y = point.y * height
        if (index === 0) context.moveTo(x, y)
        else context.lineTo(x, y)
      })
      context.stroke()
    }
  }, [strokes])

  const pointFromEvent = (event: PointerEvent<HTMLCanvasElement>): ScribblePoint => {
    const bounds = event.currentTarget.getBoundingClientRect()
    return { x: Math.max(0, Math.min(1, (event.clientX - bounds.left) / bounds.width)), y: Math.max(0, Math.min(1, (event.clientY - bounds.top) / bounds.height)) }
  }
  const startDrawing = (event: PointerEvent<HTMLCanvasElement>) => {
    if (!isDrawer || state.phase !== 'drawing' || finished) return
    event.currentTarget.setPointerCapture(event.pointerId)
    drawingRef.current = [pointFromEvent(event)]
  }
  const continueDrawing = (event: PointerEvent<HTMLCanvasElement>) => {
    if (!drawingRef.current.length) return
    drawingRef.current.push(pointFromEvent(event))
  }
  const finishDrawing = () => {
    const points = drawingRef.current
    drawingRef.current = []
    if (points.length >= 2) send({ action: 'stroke', points, color, size: 6 })
  }
  const submitGuess = (event: FormEvent) => {
    event.preventDefault()
    if (!guess.trim() || isDrawer || finished) return
    send({ action: 'guess', text: guess.trim() })
    setGuess('')
  }

  return <section className="scribble-game-shell" aria-label="Scribble drawing and guessing game">
    <header className="scribble-game-head">
      <div><span className="eyebrow">Scribble · Round {state.round ?? 1} of {state.rounds ?? 6}</span><h2>{finished ? 'What a lovely game!' : isDrawer ? 'Draw a clue for your friends.' : `${state.drawer_name ?? 'Your friend'} is drawing…`}</h2><p aria-live="polite">{isDrawer && state.word ? <>Your secret word: <strong>{state.word}</strong></> : state.last_event ?? 'Look closely, then make your best guess.'}</p></div>
      <div className="scribble-prompt"><Pencil size={22} weight="fill" /><span>{isDrawer ? 'Keep it secret' : state.hint ?? '_ _ _ _ _'}</span></div>
    </header>

    <div className="scribble-scoreboard" aria-label="Scores">
      {players.map((player, index) => <div className={index === state.current_drawer && !finished ? 'scribble-score scribble-score--active' : 'scribble-score'} key={player.name}><span className="scribble-score__avatar">{player.is_bot ? <Robot size={17} weight="fill" /> : <Pencil size={17} weight="fill" />}</span><span>{player.name}</span><strong>{state.scores?.[index] ?? 0}</strong></div>)}
    </div>

    <div className="scribble-canvas-wrap"><canvas ref={canvasRef} className={isDrawer && state.phase === 'drawing' ? 'scribble-canvas scribble-canvas--draw' : 'scribble-canvas'} onPointerDown={startDrawing} onPointerMove={continueDrawing} onPointerUp={finishDrawing} onPointerCancel={finishDrawing} aria-label={isDrawer ? 'Drawing canvas' : 'Shared drawing'} /><span className="scribble-canvas-note">{isDrawer && state.phase === 'drawing' ? 'Draw with your finger or mouse' : 'Watch the sketch and guess below'}</span></div>

    <div className="scribble-controls">
      {isDrawer && state.phase === 'drawing' && !finished && <><div className="scribble-palette" aria-label="Drawing colors">{COLORS.map((item) => <button aria-label={`Use ${item}`} className={color === item ? 'scribble-color scribble-color--selected' : 'scribble-color'} style={{ backgroundColor: item }} key={item} type="button" onClick={() => setColor(item)} />)}</div><button className="button button--secondary button--small" type="button" onClick={() => send({ action: 'clear' })}><Eraser size={17} /> Clear</button><button className="button button--primary button--small" type="button" onClick={() => send({ action: 'end_turn' })}>Finish drawing</button></>}
      {!isDrawer && !finished && <form className="scribble-guess-form" onSubmit={submitGuess}><label htmlFor="scribble-guess">Your guess</label><input id="scribble-guess" value={guess} onChange={(event) => setGuess(event.target.value)} placeholder="I think it is…" maxLength={80} /><button className="button button--primary button--small" type="submit">Guess</button></form>}
    </div>
    {error && <p className="form-error" role="alert">{error}</p>}
    {!!state.guesses?.length && <div className="scribble-guesses" aria-live="polite">{state.guesses.slice(-4).map((item, index) => <span className={item.correct ? 'scribble-guess scribble-guess--correct' : 'scribble-guess'} key={`${item.text}-${index}`}>{players[item.player]?.name}: {item.text}{item.correct ? ' ✓' : ''}</span>)}</div>}
    {finished && <div className="scribble-result" role="status"><Trophy size={25} weight="fill" /><span>{state.draw ? 'A shared tie!' : players[state.winner ?? 0]?.name + ' wins the game!'}</span><button className="button button--primary button--small game-play-again" type="button" onClick={() => send({ action: 'play_again' })}>Play again</button></div>}
    <details className="scribble-rules"><summary>How Scribble works</summary><p>One player gets a secret word and draws it. Everyone else guesses. Correct guesses earn 100 points, the drawer earns 50, and the player with the highest score after six rounds wins.</p></details>
  </section>
}
