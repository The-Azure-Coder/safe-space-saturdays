"""Server-authoritative American checkers rules.

The board uses row zero at the top. Player 0 starts at the bottom and moves up
the board; player 1 starts at the top and moves down it. Men are encoded as
1/2 and kings as 3/4 respectively.
"""

from __future__ import annotations

from typing import Any

from app.games.connect_four import IllegalMove

BOARD_SIZE = 8


def _is_dark(row: int, col: int) -> bool:
    return (row + col) % 2 == 1


def _piece_owner(piece: int) -> int | None:
    if piece in (1, 3):
        return 0
    if piece in (2, 4):
        return 1
    return None


def _is_king(piece: int) -> bool:
    return piece in (3, 4)


def _directions(piece: int) -> tuple[tuple[int, int], ...]:
    owner = _piece_owner(piece)
    if _is_king(piece) or owner is None:
        return ((-1, -1), (-1, 1), (1, -1), (1, 1))
    return ((-1, -1), (-1, 1)) if owner == 0 else ((1, -1), (1, 1))


def _inside(row: int, col: int) -> bool:
    return 0 <= row < BOARD_SIZE and 0 <= col < BOARD_SIZE


def _captures_for_piece(board: list[list[int]], row: int, col: int) -> list[dict[str, Any]]:
    piece = board[row][col]
    if not piece:
        return []
    owner = _piece_owner(piece)
    moves: list[dict[str, Any]] = []
    for row_delta, col_delta in _directions(piece):
        middle = (row + row_delta, col + col_delta)
        destination = (row + row_delta * 2, col + col_delta * 2)
        if not (_inside(*middle) and _inside(*destination)):
            continue
        jumped = board[middle[0]][middle[1]]
        if jumped and _piece_owner(jumped) != owner and board[destination[0]][destination[1]] == 0:
            moves.append({"from": [row, col], "to": list(destination), "capture": list(middle)})
    return moves


def legal_moves(state: dict[str, Any], player: int | None = None) -> list[dict[str, Any]]:
    board = state["board"]
    player = int(state["current_player"] if player is None else player)
    captures: list[dict[str, Any]] = []
    quiet: list[dict[str, Any]] = []
    forced_from = state.get("chain_piece")
    coordinates = [tuple(forced_from)] if forced_from else [(row, col) for row in range(BOARD_SIZE) for col in range(BOARD_SIZE)]
    for row, col in coordinates:
        piece = board[row][col]
        if _piece_owner(piece) != player:
            continue
        captures.extend(_captures_for_piece(board, row, col))
        if forced_from:
            continue
        for row_delta, col_delta in _directions(piece):
            destination = (row + row_delta, col + col_delta)
            if _inside(*destination) and _is_dark(*destination) and board[destination[0]][destination[1]] == 0:
                quiet.append({"from": [row, col], "to": list(destination), "capture": None})
    return captures if captures else quiet


def _initial_board() -> list[list[int]]:
    board = [[0 for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]
    for row in range(3):
        for col in range(BOARD_SIZE):
            if _is_dark(row, col):
                board[row][col] = 2
    for row in range(5, BOARD_SIZE):
        for col in range(BOARD_SIZE):
            if _is_dark(row, col):
                board[row][col] = 1
    return board


def new_checkers_state(player_count: int = 2, bot_players: tuple[int, ...] = (1,)) -> dict[str, Any]:
    if player_count != 2:
        raise IllegalMove("Checkers supports exactly two players")
    return {
        "game": "checkers",
        "current_player": 0,
        "winner": None,
        "draw": False,
        "player_count": 2,
        "players": [
            {"name": "You", "color": "coral", "is_bot": 0 in bot_players},
            {"name": "Milo Bot", "color": "sage", "is_bot": 1 in bot_players},
        ],
        "board": _initial_board(),
        "chain_piece": None,
        "legal_moves": legal_moves({"board": _initial_board(), "current_player": 0}),
        "turn_number": 1,
        "action_count": 0,
        "last_move": None,
        "last_event": "Your turn. Select a piece to see its legal moves.",
    }


def normalise_checkers_state(state: dict[str, Any]) -> None:
    state.setdefault("chain_piece", None)
    state.setdefault("draw", False)
    state.setdefault("turn_number", 1)
    state.setdefault("action_count", 0)
    state.setdefault("last_move", None)
    state.setdefault("players", [{"name": "You", "color": "coral", "is_bot": False}, {"name": "Milo Bot", "color": "sage", "is_bot": True}])
    state["player_count"] = 2
    state["legal_moves"] = legal_moves(state) if state.get("winner") is None else []


def _finish_if_needed(state: dict[str, Any]) -> None:
    current = int(state["current_player"])
    opponent = 1 - current
    pieces = [piece for row in state["board"] for piece in row]
    if not any(_piece_owner(piece) == opponent for piece in pieces) or not legal_moves(state, opponent):
        state["winner"] = current
        state["last_event"] = f"{state['players'][current]['name']} wins the game!"


def apply_checkers_action(state: dict[str, Any], player: int, action: dict[str, Any]) -> dict[str, Any]:
    normalise_checkers_state(state)
    if state.get("winner") is not None or state.get("draw"):
        raise IllegalMove("The match is already finished")
    if player != state["current_player"]:
        raise IllegalMove("It is not your turn")
    move = action.get("move") or {key: action.get(key) for key in ("from", "to")}
    origin, destination = move.get("from"), move.get("to")
    selected = next((item for item in state["legal_moves"] if item["from"] == origin and item["to"] == destination), None)
    if selected is None:
        raise IllegalMove("That checkers move is not legal")
    row, col = origin
    next_row, next_col = destination
    piece = state["board"][row][col]
    state["board"][row][col] = 0
    state["board"][next_row][next_col] = piece
    captured = selected.get("capture")
    if captured:
        state["board"][captured[0]][captured[1]] = 0
    promoted = False
    if piece == 1 and next_row == 0:
        piece = 3
        state["board"][next_row][next_col] = piece
        promoted = True
    elif piece == 2 and next_row == BOARD_SIZE - 1:
        piece = 4
        state["board"][next_row][next_col] = piece
        promoted = True
    state["action_count"] += 1
    state["last_move"] = {"player": player, "from": origin, "to": destination, "capture": captured, "promoted": promoted}
    if captured and not promoted:
        continuation = _captures_for_piece(state["board"], next_row, next_col)
        if continuation:
            state["chain_piece"] = [next_row, next_col]
            state["legal_moves"] = continuation
            state["last_event"] = f"{state['players'][player]['name']} jumped. Continue the capture."
            return state
    state["chain_piece"] = None
    state["current_player"] = 1 - player
    state["turn_number"] += 1
    state["last_event"] = f"{state['players'][player]['name']} moved. {state['players'][state['current_player']]['name']}'s turn."
    _finish_if_needed(state)
    state["legal_moves"] = legal_moves(state) if state.get("winner") is None else []
    if state.get("winner") is None and not state["legal_moves"]:
        state["winner"] = player
        state["last_event"] = f"{state['players'][player]['name']} wins — no legal moves remain."
        state["legal_moves"] = []
    return state


def checkers_bot_action(state: dict[str, Any], player: int) -> dict[str, Any]:
    moves = legal_moves(state, player)
    if not moves:
        raise IllegalMove("The bot has no legal checkers move")
    move = max(moves, key=lambda item: (item.get("capture") is not None, item["to"][0] if player == 0 else -item["to"][0]))
    return {"action": "move", "move": {"from": move["from"], "to": move["to"]}}
