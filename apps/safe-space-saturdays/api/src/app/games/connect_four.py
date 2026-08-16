from dataclasses import dataclass, replace
from typing import Literal

Player = Literal[1, 2]


@dataclass(frozen=True)
class ConnectFourState:
    board: tuple[tuple[int, ...], ...]
    current_player: Player
    winner: Player | None = None
    draw: bool = False
    move_count: int = 0
    last_move: tuple[int, int] | None = None
    winning_cells: tuple[tuple[int, int], ...] = ()


class IllegalMove(ValueError):
    """Raised when a client attempts an invalid move."""


def initial_state() -> ConnectFourState:
    board = tuple(tuple(0 for _ in range(7)) for _ in range(6))
    return ConnectFourState(board=board, current_player=1)


def _winning_cells(
    board: tuple[tuple[int, ...], ...], row: int, col: int, player: Player
) -> tuple[tuple[int, int], ...]:
    directions = ((0, 1), (1, 0), (1, 1), (1, -1))
    for row_delta, col_delta in directions:
        cells = [(row, col)]
        for sign in (1, -1):
            next_row, next_col = row + row_delta * sign, col + col_delta * sign
            while 0 <= next_row < 6 and 0 <= next_col < 7 and board[next_row][next_col] == player:
                cells.append((next_row, next_col))
                next_row += row_delta * sign
                next_col += col_delta * sign
        if len(cells) >= 4:
            return tuple(sorted(cells))
    return ()


def apply_move(state: ConnectFourState, player: Player, column: int) -> ConnectFourState:
    if state.winner is not None or state.draw:
        raise IllegalMove("The match is already finished")
    if player != state.current_player:
        raise IllegalMove("It is not your turn")
    if column < 0 or column > 6:
        raise IllegalMove("Choose a column from 1 to 7")
    row = next((index for index in range(5, -1, -1) if state.board[index][column] == 0), None)
    if row is None:
        raise IllegalMove("That column is full")
    board = [list(board_row) for board_row in state.board]
    board[row][column] = player
    frozen = tuple(tuple(board_row) for board_row in board)
    move_count = state.move_count + 1
    winning_cells = _winning_cells(frozen, row, column, player)
    winner = player if winning_cells else None
    return ConnectFourState(
        board=frozen,
        current_player=2 if player == 1 else 1,
        winner=winner,
        draw=winner is None and move_count == 42,
        move_count=move_count,
        last_move=(row, column),
        winning_cells=winning_cells,
    )


def legal_columns(state: ConnectFourState) -> list[int]:
    if state.winner is not None or state.draw:
        return []
    return [column for column in range(7) if state.board[0][column] == 0]


def choose_bot_column(state: ConnectFourState, player: Player, difficulty: str = "friendly") -> int:
    legal = legal_columns(state)
    if player != state.current_player or not legal:
        raise IllegalMove("Bot cannot move in the current state")
    ordered = sorted(legal, key=lambda column: (abs(column - 3), column))
    for column in ordered:
        if apply_move(state, player, column).winner == player:
            return column

    opponent: Player = 1 if player == 2 else 2
    opponent_turn = replace(state, current_player=opponent)
    for column in ordered:
        if apply_move(opponent_turn, opponent, column).winner == opponent:
            return column

    if difficulty != "thoughtful":
        return ordered[0]

    def evaluate(candidate: ConnectFourState, depth: int, alpha: int, beta: int) -> int:
        if candidate.winner == player:
            return 10_000 + depth
        if candidate.winner == opponent:
            return -10_000 - depth
        if candidate.draw or depth == 0:
            score = 0
            for row in candidate.board:
                score += row[3] == player
                score -= row[3] == opponent
            return score * 3
        maximizing = candidate.current_player == player
        best = -100_000 if maximizing else 100_000
        for next_column in sorted(legal_columns(candidate), key=lambda value: abs(value - 3)):
            value = evaluate(
                apply_move(candidate, candidate.current_player, next_column),
                depth - 1,
                alpha,
                beta,
            )
            if maximizing:
                best = max(best, value)
                alpha = max(alpha, best)
            else:
                best = min(best, value)
                beta = min(beta, best)
            if beta <= alpha:
                break
        return best

    return max(
        ordered,
        key=lambda column: evaluate(apply_move(state, player, column), 4, -100_000, 100_000),
    )


def serialize(state: ConnectFourState) -> dict[str, object]:
    return {
        "board": [list(row) for row in state.board],
        "current_player": state.current_player,
        "winner": state.winner,
        "draw": state.draw,
        "move_count": state.move_count,
        "last_move": list(state.last_move) if state.last_move else None,
        "winning_cells": [list(cell) for cell in state.winning_cells],
    }
