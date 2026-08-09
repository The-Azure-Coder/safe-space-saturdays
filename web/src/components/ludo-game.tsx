import { useEffect, useMemo, useRef, useState } from 'react'
import { ShieldStar, Sparkle, Trophy } from '@phosphor-icons/react'

export type LudoState = {
  seat_index?: number
  game: 'ludo'
  current_player: number
  winner: number | null
  player_count: number
  players: Array<LudoPlayer>
  positions: Array<Array<number>>
  phase: 'roll' | 'move' | 'finished'
  roll: number | null
  last_rolls: Array<number | null>
  legal_tokens: Array<number>
  captures: Array<number>
  last_event: string
  last_move: { player: number; token: number; from: number; to: number; roll: number; captured: Array<number> } | null
  action_count: number
}

type LudoGameProps = {
  state: Partial<LudoState>
  send: (action: Record<string, unknown>) => void
}

type Coordinate = readonly [number, number]
type LudoColor = 'red' | 'blue' | 'green' | 'yellow'
type LudoPlayer = { name: string; color: LudoColor; offset: number; is_bot: boolean }

const TRACK: ReadonlyArray<Coordinate> = [
  [6, 1], [6, 2], [6, 3], [6, 4], [6, 5],
  [5, 6], [4, 6], [3, 6], [2, 6], [1, 6], [0, 6],
  [0, 7], [0, 8], [1, 8], [2, 8], [3, 8], [4, 8], [5, 8],
  [6, 9], [6, 10], [6, 11], [6, 12], [6, 13], [6, 14],
  [7, 14], [8, 14], [8, 13], [8, 12], [8, 11], [8, 10], [8, 9],
  [9, 8], [10, 8], [11, 8], [12, 8], [13, 8], [14, 8],
  [14, 7], [14, 6], [13, 6], [12, 6], [11, 6], [10, 6], [9, 6],
  [8, 5], [8, 4], [8, 3], [8, 2], [8, 1], [8, 0], [7, 0], [6, 0],
]

const HOME_PATHS: Record<LudoColor, ReadonlyArray<Coordinate>> = {
  // The sixth coordinate is the shared centre. Position 57 is the finished
  // home state; keeping it on the lane made a token look stranded after a
  // legal final step.
  red: [[7, 1], [7, 2], [7, 3], [7, 4], [7, 5], [7, 7]],
  green: [[1, 7], [2, 7], [3, 7], [4, 7], [5, 7], [7, 7]],
  yellow: [[7, 13], [7, 12], [7, 11], [7, 10], [7, 9], [7, 7]],
  blue: [[13, 7], [12, 7], [11, 7], [10, 7], [9, 7], [7, 7]],
}

const YARD_SPOTS: Record<LudoColor, ReadonlyArray<Coordinate>> = {
  red: [[1.95, 1.95], [1.95, 3.15], [3.15, 1.95], [3.15, 3.15]],
  green: [[1.95, 10.95], [1.95, 12.15], [3.15, 10.95], [3.15, 12.15]],
  blue: [[10.95, 1.95], [10.95, 3.15], [12.15, 1.95], [12.15, 3.15]],
  yellow: [[10.95, 10.95], [10.95, 12.15], [12.15, 10.95], [12.15, 12.15]],
}

const SAFE_CELLS = new Set([0, 8, 13, 21, 26, 34, 39, 47])
const START_CELLS = new Set([0, 13, 26, 39])
const DEFAULT_PLAYERS: Array<LudoPlayer> = [
  { name: 'You', color: 'red', offset: 39, is_bot: false },
  { name: 'Maya Bot', color: 'green', offset: 13, is_bot: true },
]
const COLORS: Array<LudoColor> = ['blue', 'green', 'red', 'yellow']
const STACK_OFFSETS: ReadonlyArray<Coordinate> = [[-5, -5], [5, -5], [-5, 5], [5, 5]]

function normalisePositions(positions: Array<Array<number>> | undefined, count: number): Array<Array<number>> {
  return Array.from({ length: count }, (_playerValue, player) => Array.from({ length: 4 }, (_tokenValue, token) => positions?.[player]?.[token] ?? -1))
}

function tokenCoordinate(player: LudoPlayer, token: number, position: number): Coordinate {
  if (position < 0) return YARD_SPOTS[player.color][token]
  if (position < 52) return TRACK[(position + player.offset) % TRACK.length]
  return HOME_PATHS[player.color][Math.min(position - 52, HOME_PATHS[player.color].length - 1)]
}

function tokenLabel(player: LudoPlayer, token: number, position: number): string {
  const owner = player.is_bot ? `${player.name}'s` : 'Your'
  if (position < 0) return `${owner} token ${token + 1}, in the yard`
  if (position >= 57) return `${owner} token ${token + 1}, home`
  if (position >= 52) return `${owner} token ${token + 1}, in the home lane`
  return `${owner} token ${token + 1}, on track space ${position + 1}`
}

function Die({ face, rolling, label, onClick }: { face: number; rolling: boolean; label: string; onClick?: () => void }) {
  const className = rolling ? 'ludo-die ludo-die--rolling' : 'ludo-die'
  const faceMarkup = <span className={`ludo-die__face ludo-die__face--${face}`} aria-hidden="true">
    {Array.from({ length: 9 }, (_, index) => <i key={index} />)}
  </span>
  if (onClick) return <button className={`${className} ludo-die--tap`} type="button" aria-label={`${label}: ${face}. Tap to roll`} onClick={onClick}>{faceMarkup}</button>
  return <span className={className} aria-label={`${label}: ${face}`} role="img">
    {faceMarkup}
  </span>
}

function vibrate(duration: number) {
  try {
    navigator.vibrate(duration)
  } catch {
    // Vibration is optional and absent in some desktop and embedded browsers.
  }
}

export function LudoGame({ state, send }: LudoGameProps) {
  const players = state.players?.length ? state.players : DEFAULT_PLAYERS
  const targetPositions = useMemo(() => normalisePositions(state.positions, players.length), [state.positions, players.length])
  const targetSignature = JSON.stringify(targetPositions)
  const [displayPositions, setDisplayPositions] = useState<Array<Array<number>>>(targetPositions)
  const displayPositionsRef = useRef(displayPositions)
  const movementTimer = useRef<number | null>(null)
  const [isAnimatingMove, setIsAnimatingMove] = useState(false)
  const [rolling, setRolling] = useState(false)
  const [homeFlash, setHomeFlash] = useState(false)
  const [diceFace, setDiceFace] = useState(state.last_rolls?.[0] ?? 1)
  const diceTimer = useRef<number | null>(null)
  const rollFallbackTimer = useRef<number | null>(null)
  const rollStartedAt = useRef<number | null>(null)

  useEffect(() => {
    const target = JSON.parse(targetSignature) as Array<Array<number>>
    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    if (movementTimer.current !== null) window.clearInterval(movementTimer.current)
    if (reduceMotion) {
      displayPositionsRef.current = target
      setDisplayPositions(target)
      setIsAnimatingMove(false)
      return undefined
    }
    const hasMovement = target.some((tokens, player) => tokens.some((position, token) => position !== displayPositionsRef.current[player][token]))
    if (!hasMovement) return undefined
    setIsAnimatingMove(true)
    movementTimer.current = window.setInterval(() => {
      const next = displayPositionsRef.current.map((tokens, player) => tokens.map((position, token) => {
        const destination = target[player][token]
        if (position === destination) return position
        if (destination < 0 || destination < position) return destination
        if (position < 0) return 0
        return Math.min(position + 1, destination)
      }))
      displayPositionsRef.current = next
      setDisplayPositions(next)
      if (next.every((tokens, player) => tokens.every((position, token) => position === target[player][token]))) {
        if (movementTimer.current !== null) window.clearInterval(movementTimer.current)
        movementTimer.current = null
        setIsAnimatingMove(false)
      }
    }, 310)
    return () => {
      if (movementTimer.current !== null) window.clearInterval(movementTimer.current)
      movementTimer.current = null
    }
  }, [targetSignature])

  const homeMoveSignature = state.last_move?.to === 57
    ? `${state.last_move.player}-${state.last_move.token}-${state.last_move.to}`
    : ''
  useEffect(() => {
    if (!homeMoveSignature) return undefined
    setHomeFlash(true)
    const timer = window.setTimeout(() => setHomeFlash(false), 950)
    return () => window.clearTimeout(timer)
  }, [homeMoveSignature])

  useEffect(() => {
    if (!rolling || rollStartedAt.current === null || (state.action_count ?? 0) <= rollStartedAt.current) return undefined
    const settleTimer = window.setTimeout(() => {
      if (diceTimer.current !== null) window.clearInterval(diceTimer.current)
      if (rollFallbackTimer.current !== null) window.clearTimeout(rollFallbackTimer.current)
      diceTimer.current = null
      rollFallbackTimer.current = null
      setDiceFace(state.last_rolls?.[0] ?? state.roll ?? 1)
      setRolling(false)
      rollStartedAt.current = null
    }, 900)
    return () => window.clearTimeout(settleTimer)
  }, [rolling, state.action_count, state.last_rolls, state.roll])

  useEffect(() => () => {
    if (diceTimer.current !== null) window.clearInterval(diceTimer.current)
    if (rollFallbackTimer.current !== null) window.clearTimeout(rollFallbackTimer.current)
    if (movementTimer.current !== null) window.clearInterval(movementTimer.current)
  }, [])

  const winner = state.winner ?? null
  const currentPlayer = state.current_player ?? 0
  const localPlayer = state.seat_index ?? 0
  const phase = state.phase ?? 'roll'
  const legalTokens = state.legal_tokens ?? []
  const canRoll = currentPlayer === localPlayer && phase === 'roll' && winner === null && !rolling && !isAnimatingMove
  const canMove = currentPlayer === localPlayer && phase === 'move' && winner === null && !rolling && !isAnimatingMove
  const activePlayer = players[currentPlayer] ?? players[localPlayer] ?? players[0]
  const botRolling = currentPlayer !== localPlayer && Boolean(players[currentPlayer]?.is_bot) && phase === 'roll' && winner === null

  const rollDice = () => {
    if (!canRoll) return
    rollStartedAt.current = state.action_count ?? 0
    setRolling(true)
    diceTimer.current = window.setInterval(() => setDiceFace((face) => face % 6 + 1), 130)
    rollFallbackTimer.current = window.setTimeout(() => {
      if (diceTimer.current !== null) window.clearInterval(diceTimer.current)
      diceTimer.current = null
      rollFallbackTimer.current = null
      rollStartedAt.current = null
      setRolling(false)
    }, 8_000)
    vibrate(35)
    send({ action: 'roll' })
  }

  const moveToken = (token: number) => {
    if (!canMove || !legalTokens.includes(token)) return
    vibrate(25)
    send({ action: 'move', token })
  }

  const turnMessage = winner !== null
    ? winner === localPlayer ? 'You brought every token home!' : `${players[winner]?.name ?? 'A bot'} brought every token home.`
    : rolling ? 'The dice is tumbling…'
      : isAnimatingMove ? 'A token is travelling along the path…'
        : currentPlayer !== localPlayer ? `${activePlayer.name} is taking a thoughtful turn…`
          : phase === 'move' ? 'Choose one of the glowing tokens.'
            : 'Your turn — roll the dice.'

  return <section className="ludo-game-shell" aria-label={`Ludo game with ${players.length} players`}>
    <div className="ludo-scoreboard">
      <div className="ludo-round-status" aria-live="polite">
        <span className="eyebrow">Friendly Ludo · {players.length} players</span>
        <strong>{turnMessage}</strong>
      </div>
    </div>

    <div className="ludo-board-frame">
      <div className="ludo-classic-board" role="grid" aria-label="Classic fifteen by fifteen Ludo board">
        {COLORS.map((color) => {
          const playerIndex = players.findIndex((player) => player.color === color)
          const playerName = playerIndex >= 0 ? players[playerIndex].name : color
          const active = playerIndex >= 0 && currentPlayer === playerIndex && winner === null
          const playerRolling = playerIndex === localPlayer ? rolling : botRolling && currentPlayer === playerIndex
          return <div className={`ludo-yard ludo-yard--${color}${active ? ' ludo-yard--active' : ''}`} aria-label={`${playerName} yard${active ? ', current turn' : ''}`} key={color}><span>{playerName}</span>{active && <><small className="ludo-yard__turn">{phase === 'roll' ? 'ROLL' : 'MOVE'}</small><span className="ludo-yard__die"><Die face={state.last_rolls?.[playerIndex] ?? (playerIndex === localPlayer ? diceFace : 1)} rolling={playerRolling} label={`${playerName} die`} onClick={playerIndex === localPlayer && canRoll ? rollDice : undefined} /></span></>}<div className="ludo-yard__inner">{Array.from({ length: 4 }, (_, index) => <i key={index} />)}</div></div>
        })}

        {TRACK.map(([row, column], index) => <span
          className={`ludo-track-square${SAFE_CELLS.has(index) ? ' ludo-track-square--safe' : ''}${START_CELLS.has(index) ? ` ludo-track-square--start ludo-track-square--start-${index}` : ''}`}
          style={{ gridRow: row + 1, gridColumn: column + 1 }}
          role="gridcell"
          aria-label={`Track space ${index + 1}${SAFE_CELLS.has(index) ? ', safe' : ''}`}
          key={`track-${index}`}
        >{SAFE_CELLS.has(index) && <ShieldStar size={13} weight="fill" aria-hidden="true" />}</span>)}

        {COLORS.flatMap((color) => HOME_PATHS[color].map(([row, column], index) => <span className={`ludo-home-square ludo-home-square--${color}`} style={{ gridRow: row + 1, gridColumn: column + 1 }} key={`${color}-home-${index}`} />))}
        <div className={`ludo-finish${homeFlash ? ' ludo-finish--sparkle' : ''}`} aria-label="Home"><Sparkle size={30} weight="fill" /><span>HOME</span></div>

        {displayPositions.flatMap((tokens, player) => tokens.map((position, token) => {
          if (position >= 57) return null
          const playerDetails = players[player]
          const [row, column] = tokenCoordinate(playerDetails, token, position)
          const occupants = displayPositions.flatMap((otherTokens, otherPlayer) => otherTokens.map((otherPosition, otherToken) => {
            const [otherRow, otherColumn] = tokenCoordinate(players[otherPlayer], otherToken, otherPosition)
            return { key: `${otherPlayer}-${otherToken}`, row: otherRow, column: otherColumn }
          })).filter((occupant) => occupant.row === row && occupant.column === column)
          const occupantIndex = occupants.findIndex((occupant) => occupant.key === `${player}-${token}`)
          const [stackX, stackY] = occupants.length > 1 ? STACK_OFFSETS[occupantIndex % STACK_OFFSETS.length] : [0, 0]
          const legal = player === localPlayer && canMove && legalTokens.includes(token)
          const hopping = position !== targetPositions[player][token]
          const tokenClass = `ludo-token ludo-token--${playerDetails.color}${position < 0 ? ' ludo-token--yard' : ''}${legal ? ' ludo-token--legal' : ''}`
          return <span className={`ludo-token-slot${hopping ? ' ludo-token-slot--hopping' : ''}`} style={{ left: `${((column + 0.5) / 15) * 100}%`, top: `${((row + 0.5) / 15) * 100}%`, marginLeft: stackX, marginTop: stackY }} key={`${player}-${token}`}>
            {player === localPlayer ? <button
              className={tokenClass}
              type="button"
              aria-label={`${tokenLabel(playerDetails, token, position)}${legal ? ', legal move' : ''}`}
              disabled={!legal}
              onClick={() => moveToken(token)}
            ><span>{token + 1}</span></button> : <span className={tokenClass} aria-label={tokenLabel(playerDetails, token, position)} role="img"><span>{token + 1}</span></span>}
          </span>
        }))}
      </div>
    </div>

    {winner !== null && <div className="ludo-winner-banner" role="status"><Trophy size={26} weight="fill" /><div><strong>{winner === localPlayer ? 'Beautiful win!' : 'Good game!'}</strong><span>{winner === localPlayer ? 'All four tokens made it safely home.' : `${players[winner]?.name ?? 'A bot'} won this round.`}</span></div><button className="button button--small button--primary game-play-again" type="button" onClick={() => send({ action: 'play_again' })}>Play again</button></div>}
    <details className="ludo-rules"><summary>How this Ludo match works</summary><div><p>Roll a six to leave the yard. Choose any glowing token, move by the exact dice value, and bring all four tokens home.</p><p>Shield spaces are safe. Landing on another player elsewhere sends that token back to its yard. A six, capture, or finished token earns another roll; three sixes ends the turn.</p></div></details>
  </section>
}
