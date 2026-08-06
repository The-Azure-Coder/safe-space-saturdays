from dataclasses import dataclass
from typing import Literal

Player = Literal[1, 2]


@dataclass(frozen=True)
class ConnectFourState:
    board: tuple[tuple[int, ...], ...]
    current_player: Player
    winner: Player | None = None
    draw: bool = False
    move_count: int = 0


class IllegalMove(ValueError):
    """Raised when a client attempts an invalid move."""


def initial_state() -> ConnectFourState:
    board = tuple(tuple(0 for _ in range(7)) for _ in range(6))
    return ConnectFourState(board=board, current_player=1)


def _has_four(board: tuple[tuple[int, ...], ...], row: int, col: int, player: Player) -> bool:
    directions = ((0, 1), (1, 0), (1, 1), (1, -1))
    for row_delta, col_delta in directions:
        count = 1
        for sign in (1, -1):
            next_row, next_col = row + row_delta * sign, col + col_delta * sign
            while 0 <= next_row < 6 and 0 <= next_col < 7 and board[next_row][next_col] == player:
                count += 1
                next_row += row_delta * sign
                next_col += col_delta * sign
        if count >= 4:
            return True
    return False


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
    winner = player if _has_four(frozen, row, column, player) else None
    return ConnectFourState(
        board=frozen,
        current_player=2 if player == 1 else 1,
        winner=winner,
        draw=winner is None and move_count == 42,
        move_count=move_count,
    )


def legal_columns(state: ConnectFourState) -> list[int]:
    if state.winner is not None or state.draw:
        return []
    return [column for column in range(7) if state.board[0][column] == 0]


def choose_bot_column(state: ConnectFourState, player: Player, difficulty: str = "friendly") -> int:
    legal = legal_columns(state)
    if player != state.current_player or not legal:
        raise IllegalMove("Bot cannot move in the current state")
    if difficulty == "thoughtful":
        for column in legal:
            try:
                if apply_move(state, player, column).winner == player:
                    return column
            except IllegalMove:
                continue
    return min(legal, key=lambda column: abs(column - 3))


def serialize(state: ConnectFourState) -> dict[str, object]:
    return {
        "board": [list(row) for row in state.board],
        "current_player": state.current_player,
        "winner": state.winner,
        "draw": state.draw,
        "move_count": state.move_count,
    }
