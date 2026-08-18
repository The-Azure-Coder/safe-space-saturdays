import { useMemo, useState } from 'react'
import { Crown, Sparkle } from '@phosphor-icons/react'

export type CheckersState = {
  board?: number[][]
  current_player?: number
  winner?: number | null
  draw?: boolean
  players?: Array<{ name: string; color: string; is_bot: boolean }>
  legal_moves?: Array<{ from: number[]; to: number[]; capture?: number[] | null }>
  last_event?: string
  chain_piece?: number[] | null
  seat_index?: number
}

export function CheckersGame({ state, send }: { state: Partial<CheckersState>; send: (action: Record<string, unknown>) => void }) {
  const [selected, setSelected] = useState<number[] | null>(null)
  const board = state.board ?? Array.from({ length: 8 }, () => Array(8).fill(0))
  const seat = Number(state.seat_index ?? 0)
  const moves = state.legal_moves ?? []
  const selectedMoves = useMemo(() => selected ? moves.filter((move) => move.from[0] === selected[0] && move.from[1] === selected[1]) : [], [moves, selected])
  const canAct = state.winner === null && state.current_player === seat
  const isTarget = (row: number, col: number) => selectedMoves.some((move) => move.to[0] === row && move.to[1] === col)
  const choose = (row: number, col: number) => {
    if (!canAct) return
    if (isTarget(row, col)) {
      send({ action: 'move', move: { from: selected, to: [row, col] } })
      setSelected(null)
      return
    }
    if (moves.some((move) => move.from[0] === row && move.from[1] === col)) setSelected([row, col])
  }
  const player = state.players?.[Number(state.current_player ?? 0)]
  return <section className="mini-game-card checkers-game" aria-label="Checkers game">
    <div className="checkers-game__header">
      <div><span className="eyebrow">American checkers · 2 players</span><h2>{state.winner !== null && state.winner !== undefined ? `${state.players?.[state.winner]?.name ?? 'Player'} wins!` : `${player?.name ?? 'Player'}'s turn`}</h2><p>{state.last_event ?? 'Select one of your pieces.'}</p></div>
      <div className="checkers-game__rule"><Sparkle size={18} weight="fill" /> Captures are required</div>
    </div>
    <div className="checkers-game__players">
      {(state.players ?? []).map((entry, index) => <div className={`checkers-player ${state.current_player === index ? 'is-active' : ''}`} key={`${entry.name}-${index}`}><span className={`checkers-player__dot checkers-player__dot--${entry.color}`} /> <span>{entry.name}{entry.is_bot ? ' · Bot' : ''}</span><small>{state.current_player === index ? 'Playing' : 'Waiting'}</small></div>)}
    </div>
    <div className="checkers-board" role="grid" aria-label="Checkers board">
      {board.map((row, rowIndex) => row.map((piece, colIndex) => {
        const dark = (rowIndex + colIndex) % 2 === 1
        const chosen = selected?.[0] === rowIndex && selected?.[1] === colIndex
        const target = isTarget(rowIndex, colIndex)
        const owner = piece === 1 || piece === 3 ? 0 : piece === 2 || piece === 4 ? 1 : null
        return <button className={`checkers-square ${dark ? 'is-dark' : 'is-light'} ${chosen ? 'is-selected' : ''} ${target ? 'is-target' : ''}`} key={`${rowIndex}-${colIndex}`} type="button" role="gridcell" aria-label={`${String.fromCharCode(65 + colIndex)}${8 - rowIndex}${owner === null ? '' : ` ${state.players?.[owner]?.name ?? 'piece'}`}`} onClick={() => choose(rowIndex, colIndex)}>
          {target && <span className="checkers-target" aria-hidden="true" />}
          {piece !== 0 && <span className={`checkers-piece checkers-piece--${owner === 0 ? 'coral' : 'sage'} ${piece > 2 ? 'is-king' : ''}`}>{piece > 2 && <Crown size={18} weight="fill" aria-label="King" />}</span>}
        </button>
      }))}
    </div>
    <p className="checkers-game__help">{state.chain_piece ? 'Continue your capture with the same piece.' : canAct ? 'Tap a piece, then tap a highlighted square.' : 'Your opponent is thinking.'}</p>
  </section>
}
