import { useEffect, useMemo, useRef, useState } from 'react'
import type { CSSProperties } from 'react'
import { ArrowBendDownLeft, ArrowBendDownRight, Robot, Sparkle, Trophy } from '@phosphor-icons/react'

type DominoPlayer = { name: string; is_bot: boolean }
type DominoMove = { tile_index: number; sides: Array<'left' | 'right'> }

export type DominoState = {
  seat_index?: number
  game: 'dominoes'
  current_player: number
  player_count: number
  players: Array<DominoPlayer>
  winner: number | null
  draw: boolean
  hands: Array<Array<[number, number]>>
  hand_counts: Array<number>
  board: Array<[number, number]>
  passes: number
  turn_number: number
  action_count: number
  legal_moves: Array<DominoMove>
  last_move: { player: number; tile?: [number, number]; side?: 'left' | 'right'; pass: boolean } | null
  last_event: string
}

type DominoGameProps = {
  state: Partial<DominoState>
  send: (action: Record<string, unknown>) => void
  error?: string
  playerIndex?: number
}

type DominoLayout = { x: number; y: number; vertical: boolean; reverse: boolean }

function createDominoLayout(board: Array<[number, number]>): Array<DominoLayout> {
  const layout: Array<DominoLayout> = []
  let row = 0
  let direction = 1
  let currentX = 1
  let lastX = 1
  let hasHorizontal = false

  for (let index = 0; index < board.length; index += 1) {
    if (currentX < 1 || currentX > 6) {
      const turnX = hasHorizontal ? lastX + direction * 0.5 : direction === 1 ? 0.5 : 6.5
      layout.push({ x: turnX, y: row + 1, vertical: true, reverse: false })
      row += 1
      direction *= -1
      currentX = turnX + direction * 0.5
      hasHorizontal = false
      continue
    }

    layout.push({ x: currentX, y: row + 0.5, vertical: false, reverse: direction < 0 })
    lastX = currentX
    currentX += direction
    hasHorizontal = true
  }
  return layout
}

const PIP_CELLS: Record<number, Array<number>> = {
  0: [],
  1: [4],
  2: [0, 8],
  3: [0, 4, 8],
  4: [0, 2, 6, 8],
  5: [0, 2, 4, 6, 8],
  6: [0, 2, 3, 5, 6, 8],
}

const DEFAULT_PLAYERS: Array<DominoPlayer> = [
  { name: 'You', is_bot: false },
  { name: 'Milo Bot', is_bot: true },
]

function PipFace({ value }: { value: number }) {
  const pips = new Set(PIP_CELLS[value] ?? [])
  return <span className="domino-face" aria-hidden="true">
    {Array.from({ length: 9 }, (_, index) => <i className={pips.has(index) ? 'domino-pip domino-pip--on' : 'domino-pip'} key={index} />)}
  </span>
}

function DominoTile({
  tile,
  className = '',
}: {
  tile: [number, number]
  className?: string
}) {
  return <span className={`domino-piece${tile[0] === tile[1] ? ' domino-piece--double' : ''}${className ? ` ${className}` : ''}`} aria-label={`${tile[0]}–${tile[1]}`} role="img">
    <PipFace value={tile[0]} />
    <span className="domino-piece__bar" aria-hidden="true" />
    <PipFace value={tile[1]} />
  </span>
}

export function DominoGame({ state, send, error = '', playerIndex }: DominoGameProps) {
  const players = state.players?.length ? state.players : DEFAULT_PLAYERS
  const hands = state.hands ?? [[], []]
  const board = state.board ?? []
  const dominoLayout = useMemo(() => createDominoLayout(board), [board])
  const legalMoves = state.legal_moves ?? []
  const currentPlayer = state.current_player ?? 0
  const localPlayer = playerIndex ?? state.seat_index ?? 0
  const winner = state.winner ?? null
  const draw = state.draw ?? false
  const [selectedTile, setSelectedTile] = useState<number | null>(null)
  const [placing, setPlacing] = useState(false)
  const chainRef = useRef<HTMLDivElement | null>(null)
  const actionSignature = state.action_count ?? 0

  useEffect(() => {
    setSelectedTile(null)
    setPlacing(false)
  }, [actionSignature])

  useEffect(() => {
    if (error) setPlacing(false)
  }, [error])

  useEffect(() => {
    chainRef.current?.querySelector('.domino-chain__cell--new')?.scrollIntoView({
      behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth',
      block: 'nearest',
      inline: 'nearest',
    })
  }, [actionSignature])

  const legalByIndex = useMemo(
    () => new Map(legalMoves.map((move) => [move.tile_index, move.sides])),
    [legalMoves],
  )
  const selectedSides = selectedTile === null ? [] : legalByIndex.get(selectedTile) ?? []
  const canAct = currentPlayer === localPlayer && winner === null && !draw && !placing
  const activeName = players[currentPlayer]?.name ?? 'A player'
  const winnerName = winner === null ? 'A player' : players[winner]?.name ?? 'A player'
  const leftEnd = board.length ? board[0][0] : null
  const rightEnd = board.length ? board[board.length - 1][1] : null

  const playTile = (index: number) => {
    if (!canAct) return
    const sides = legalByIndex.get(index)
    if (!sides?.length) return
    if (sides.length === 1) {
      setPlacing(true)
      send({ tile_index: index, side: sides[0] })
      return
    }
    setSelectedTile((current) => current === index ? null : index)
  }

  const chooseSide = (side: 'left' | 'right') => {
    if (selectedTile === null || !selectedSides.includes(side)) return
    setPlacing(true)
    send({ tile_index: selectedTile, side })
  }

  const pass = () => {
    if (!canAct || legalMoves.length) return
    setPlacing(true)
    send({ pass: true })
  }

  const turnMessage = winner !== null
    ? winner === localPlayer ? 'You cleared your hand!' : `${players[winner]?.name ?? 'A player'} cleared their hand.`
    : draw ? 'This blocked round ended in a tie.'
      : placing ? 'Your domino is sliding into place…'
        : currentPlayer === localPlayer
          ? legalMoves.length ? 'Your turn — choose a glowing domino.' : 'No match available — pass the turn.'
          : `${activeName} is studying the open ends…`

  return <section className="domino-game-shell" aria-label={`Block Dominoes with ${players.length} players`}>
    <header className="domino-game-head">
      <div><span className="eyebrow">Block Dominoes · {players.length} players</span><h2 aria-live="polite">{turnMessage}</h2><p>{state.last_event ?? 'Match one side of a domino to an open end.'}</p></div>
      <div className="domino-end-readout" aria-label="Open ends">
        <span><small>Left end</small><strong>{leftEnd ?? 'Open'}</strong></span>
        <Sparkle size={18} weight="fill" aria-hidden="true" />
        <span><small>Right end</small><strong>{rightEnd ?? 'Open'}</strong></span>
      </div>
    </header>

    <div className="domino-opponents" aria-label="Other players">
      {players.map((player, index) => {
        if (index === localPlayer) return null
        const playerIndex = index
        const handCount = state.hand_counts?.[playerIndex] ?? hands[playerIndex].length
        return <article className={`domino-player${currentPlayer === playerIndex && winner === null && !draw ? ' domino-player--active' : ''}`} key={player.name}>
          <span className="domino-player__avatar"><Robot size={20} weight="fill" /></span>
          <span><strong>{player.name}</strong><small>{handCount} dominoes</small></span>
          <span className="domino-mini-rack" aria-hidden="true">{Array.from({ length: Math.min(5, handCount) }, (_, tile) => <i key={tile} />)}</span>
        </article>
      })}
    </div>

    <div className="domino-table-wrap">
      <div className="domino-table-2d" aria-label="Domino table" role="region">
        {board.length === 0 ? <div className="domino-table-empty"><Sparkle size={28} weight="fill" /><strong>The table is open</strong><span>Choose any domino to begin the chain.</span></div> : <div ref={chainRef} className="domino-chain" style={{ '--domino-rows': Math.max(2, Math.ceil(Math.max(...dominoLayout.map(({ y }) => y + 0.5))) ) } as CSSProperties}>
          {board.map((tile, index) => {
            const placement = dominoLayout[index]
            const newest = state.last_move?.tile && ((state.last_move.side === 'left' && index === 0) || (state.last_move.side !== 'left' && index === board.length - 1))
            return <span className={`domino-chain__cell${placement.reverse ? ' domino-chain__cell--reverse' : ''}${placement.vertical ? ' domino-chain__cell--turn' : ''}${newest ? ` domino-chain__cell--new domino-chain__cell--from-${state.last_move?.side ?? 'right'}` : ''}`} style={{ '--domino-x': placement.x, '--domino-y': placement.y } as CSSProperties} key={`${index}-${tile[0]}-${tile[1]}`}>
              <DominoTile tile={tile} className={placement.reverse ? 'domino-piece--reverse' : ''} />
            </span>
          })}
        </div>}
      </div>
    </div>

    {selectedTile !== null && selectedSides.length > 1 && <div className="domino-end-chooser" role="group" aria-label="Choose an open end">
      <span>Where should this domino go?</span>
      <button type="button" onClick={() => chooseSide('left')}><ArrowBendDownLeft size={19} /> Left · {leftEnd}</button>
      <button type="button" onClick={() => chooseSide('right')}>Right · {rightEnd} <ArrowBendDownRight size={19} /></button>
    </div>}

    <section className="domino-hand" aria-labelledby="your-dominoes-title">
      <div className="domino-hand__head"><div><span className="eyebrow">Your hand</span><h3 id="your-dominoes-title">{hands[localPlayer]?.length ?? 0} dominoes</h3></div><button className="button button--secondary button--small" type="button" disabled={!canAct || legalMoves.length > 0} onClick={pass}>Pass turn</button></div>
      <div className="domino-hand__tiles">
        {(hands[localPlayer] ?? []).map((tile, index) => {
          const legal = canAct && legalByIndex.has(index)
          return <button className={`domino-hand-tile${legal ? ' domino-hand-tile--legal' : ''}${selectedTile === index ? ' domino-hand-tile--selected' : ''}`} type="button" disabled={!legal} onClick={() => playTile(index)} aria-label={`Play ${tile[0]}–${tile[1]}${legal ? '' : ', no matching end'}`} key={`${index}-${tile[0]}-${tile[1]}`}>
            <DominoTile tile={tile} />
          </button>
        })}
      </div>
    </section>

    {(winner !== null || draw) && <div className="domino-result" role="status"><Trophy size={26} weight="fill" /><div><strong>{draw ? 'Evenly matched!' : winner === localPlayer ? 'Beautifully played!' : 'Good round!'}</strong><span>{draw ? 'The chain blocked with equal low pip totals.' : winner === localPlayer ? 'You placed every domino first.' : `${winnerName} won this round.`}</span></div><button className="button button--small button--primary game-play-again" type="button" onClick={() => send({ action: 'play_again' })}>Play again</button></div>}
    <details className="domino-rules"><summary>How Block Dominoes works</summary><div><p>Match either half of a domino to the same number on an open end. If it fits both ends, choose where to place it.</p><p>When no domino matches, pass. The round ends when someone clears their hand or every player passes; on a blocked table, the lowest remaining pip total wins.</p></div></details>
  </section>
}
