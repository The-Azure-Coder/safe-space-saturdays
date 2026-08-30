"""Small, deterministic game engines used by the shared match transport.

The browser sends intentions only. Every random value, legal-move check, score, and
winner is decided here on the server.
"""

from __future__ import annotations

import random
from typing import Any

from app.games.connect_four import IllegalMove
from app.games.scribble import apply_scribble_action, bot_draw_action, new_scribble_state
from app.games.trivia import apply_trivia_action, new_trivia_state, trivia_bot_action
from app.games.abc_fast_slow import abc_bot_action, apply_abc_action, new_abc_state, next_abc_round
from app.games.checkers import checkers_bot_action, apply_checkers_action, new_checkers_state, normalise_checkers_state
from app.games.together import apply_together_action, new_together_state
from app.games.csec_exam import apply_csec_exam_action, new_csec_exam_state

GAME_TYPES = {"ludo", "dominoes", "bingo", "trivia", "scribble", "abc-fast-slow", "checkers", "together", "csec-it-mock-exam"}
_RNG = random.Random()
# 52-56 are the five coloured home-lane squares; 57 is the centre HOME.
LUDO_FINISH = 57
LUDO_TRACK_LENGTH = 52
LUDO_SEATS = {
    "red": {"offset": 0, "name": "You"},
    "green": {"offset": 13, "name": "Maya Bot"},
    "yellow": {"offset": 26, "name": "Sunny Bot"},
    "blue": {"offset": 39, "name": "Milo Bot"},
}
# Matches the reference game's supported combinations: opposite seats for two,
# three occupied corners for three, and every yard for four.
LUDO_PLAYER_COLORS = {
    2: ("red", "green"),
    3: ("red", "blue", "yellow"),
    4: ("red", "blue", "green", "yellow"),
}
LUDO_SAFE_CELLS = frozenset({0, 8, 13, 21, 26, 34, 39, 47})


def _turn(state: dict[str, Any], player: int) -> None:
    if state["winner"] is not None or state.get("draw", False):
        raise IllegalMove("The match is already finished")
    if state["current_player"] != player:
        raise IllegalMove("It is not your turn")


def _ludo_players(player_count: int) -> list[dict[str, Any]]:
    player_count = max(2, min(4, player_count))
    return [
        {
            "name": "You" if index == 0 else LUDO_SEATS[color]["name"],
            "color": color,
            "offset": LUDO_SEATS[color]["offset"],
            "is_bot": index != 0,
        }
        for index, color in enumerate(LUDO_PLAYER_COLORS[player_count])
    ]


def _domino_players(player_count: int) -> list[dict[str, Any]]:
    names = ("You", "Milo Bot", "Maya Bot", "Sunny Bot")
    return [
        {"name": names[index], "is_bot": index != 0}
        for index in range(max(2, min(4, player_count)))
    ]


def _deal_domino_hands(player_count: int, starting_player: int, force_double_six: bool) -> list[list[list[int]]]:
    deck = [[left, right] for left in range(7) for right in range(left, 7)]
    _RNG.shuffle(deck)
    hands = [deck[index * 7 : index * 7 + 7] for index in range(max(2, min(4, player_count)))]
    if force_double_six:
        owner = max(0, min(len(hands) - 1, starting_player))
        current = hands[owner][0]
        double_six_owner = next((hand for hand in hands if [6, 6] in hand), None)
        if double_six_owner is not None:
            double_six_owner[double_six_owner.index([6, 6])] = current
        hands[owner][0] = [6, 6]
    return hands


def new_state(
    game_type: str, player_count: int = 2, bot_players: tuple[int, ...] | None = None,
    bot_difficulty: str = "friendly",
) -> dict[str, Any]:
    if game_type not in GAME_TYPES:
        raise IllegalMove("This game is not available yet")
    if game_type == "together":
        return new_together_state(player_count)
    if game_type == "csec-it-mock-exam":
        return new_csec_exam_state(player_count)
    if game_type == "ludo":
        players = _ludo_players(player_count)
        return {
            "game": "ludo",
            "current_player": 0,
            "winner": None,
            "player_count": len(players),
            "players": players,
            "positions": [[-1, -1, -1, -1] for _ in players],
            "phase": "roll",
            "roll": None,
            "legal_tokens": [],
            "six_streak": 0,
            "turn_number": 1,
            "action_count": 0,
            "captures": [0 for _ in players],
            "last_rolls": [None for _ in players],
            "last_move": None,
            "last_event": "Your turn. Roll the dice to begin.",
        }
    if game_type == "dominoes":
        players = _domino_players(player_count)
        hands = _deal_domino_hands(len(players), 0, True)
        return {
            "game": "dominoes",
            "current_player": 0,
            "winner": None,
            "draw": False,
            "player_count": len(players),
            "players": players,
            "hands": hands,
            "board": [],
            "passes": 0,
            "turn_number": 1,
            "action_count": 0,
            "last_move": None,
            "round": 1,
            "rounds": 6,
            "round_wins": [0 for _ in players],
            "round_winner": None,
            "starting_player": 0,
            "opening_tile_required": True,
            "last_event": "Double six opens round one.",
            "legal_moves": [{"tile_index": 0, "sides": ["right"]}],
        }
    if game_type == "bingo":
        numbers = list(range(1, 76))
        _RNG.shuffle(numbers)
        player_count = max(2, min(8, player_count))
        cards: list[list[list[int]]] = []
        for player in range(player_count):
            card = [
                sorted(numbers[player * 25 + index * 5 : player * 25 + index * 5 + 5])
                for index in range(5)
            ]
            card[2][2] = 0
            cards.append(card)
        marked_cards = [
            [[row == 2 and col == 2 for col in range(5)] for row in range(5)] for _ in cards
        ]
        return {
            "game": "bingo",
            "current_player": 0,
            "winner": None,
            "draw": False,
            "player_count": player_count,
            "cards": cards,
            "marked_cards": marked_cards,
            # Compatibility aliases for early clients/tests; snapshots expose only
            # the requesting player's card and marked state.
            "card": cards[0],
            "marked": marked_cards[0],
            "drawn": [],
            "remaining": list(range(1, 76)),
        }
    if game_type == "scribble":
        return new_scribble_state(_RNG, player_count, bot_players if bot_players is not None else (1,))
    if game_type == "abc-fast-slow":
        return new_abc_state(_RNG, player_count, bot_players if bot_players is not None else (1,))
    if game_type == "checkers":
        return new_checkers_state(player_count, bot_players if bot_players is not None else (1,))
    return new_trivia_state(_RNG, player_count, bot_players if bot_players is not None else (1,))


def _next_player(state: dict[str, Any]) -> None:
    player_count = int(state.get("player_count", len(state.get("positions", [0, 1]))))
    state["current_player"] = (state["current_player"] + 1) % player_count


def _roll_die() -> int:
    return _RNG.randint(1, 6)


def normalise_ludo_state(state: dict[str, Any], player_count: int | None = None) -> None:
    """Hydrate fields added after early persisted Ludo matches were created."""
    requested_count = max(2, min(4, player_count or int(state.get("player_count", 2))))
    old_players = state.get("players", [])
    players = _ludo_players(requested_count)
    if isinstance(old_players, list):
        for index, old_player in enumerate(old_players[:requested_count]):
            if isinstance(old_player, dict):
                if old_player.get("name"):
                    players[index]["name"] = old_player["name"]
                if "is_bot" in old_player:
                    players[index]["is_bot"] = bool(old_player["is_bot"])
    old_positions = state.get("positions", [])
    old_captures = state.get("captures", [])
    old_rolls = state.get("last_rolls", [])
    state["player_count"] = requested_count
    state["players"] = players
    state["positions"] = [
        list(old_positions[index][:4]) if index < len(old_positions) else [-1, -1, -1, -1]
        for index in range(requested_count)
    ]
    state["captures"] = [
        old_captures[index] if index < len(old_captures) else 0 for index in range(requested_count)
    ]
    state["last_rolls"] = [
        old_rolls[index] if index < len(old_rolls) else None for index in range(requested_count)
    ]
    if int(state.get("current_player", 0)) >= requested_count:
        state["current_player"] = 0
    state.setdefault("phase", "roll")
    state.setdefault("legal_tokens", [])
    state.setdefault("six_streak", 0)
    state.setdefault("turn_number", 1)
    state.setdefault("action_count", 0)
    state.setdefault("last_move", None)


def normalise_bingo_state(state: dict[str, Any], player_count: int = 2) -> None:
    if "cards" in state and "marked_cards" in state:
        return
    legacy_card = state.pop("card", None)
    legacy_marked = state.pop("marked", None)
    replacement = new_state("bingo", max(2, min(8, player_count)))
    cards = replacement["cards"]
    marked_cards = replacement["marked_cards"]
    if legacy_card is not None:
        cards[0] = legacy_card
    if legacy_marked is not None:
        marked_cards[0] = legacy_marked
    state["cards"] = cards
    state["marked_cards"] = marked_cards
    state["card"] = cards[0]
    state["marked"] = marked_cards[0]
    state.setdefault("player_count", len(cards))
    state.setdefault("drawn", [])
    state.setdefault("remaining", list(range(1, 76)))
    state.setdefault("last_event", "Roll the dice.")


def _ludo_global_cell(state: dict[str, Any], player: int, position: int) -> int | None:
    if not 0 <= position < LUDO_TRACK_LENGTH:
        return None
    return (position + int(state["players"][player]["offset"])) % LUDO_TRACK_LENGTH


def _ludo_legal_tokens(state: dict[str, Any], player: int, roll: int) -> list[int]:
    legal: list[int] = []
    for token, position in enumerate(state["positions"][player]):
        if position == -1 and roll == 6:
            legal.append(token)
        elif 0 <= position < LUDO_FINISH and position + roll <= LUDO_FINISH:
            legal.append(token)
    return legal


def _ludo_switch_turn(state: dict[str, Any], message: str) -> None:
    _next_player(state)
    state["phase"] = "roll"
    state["legal_tokens"] = []
    state["six_streak"] = 0
    state["turn_number"] += 1
    state["last_event"] = message


def _ludo_captures(state: dict[str, Any], player: int, position: int) -> list[int]:
    destination = _ludo_global_cell(state, player, position)
    if destination is None or destination in LUDO_SAFE_CELLS:
        return []
    captured: list[int] = []
    for opponent, opponent_tokens in enumerate(state["positions"]):
        if opponent == player:
            continue
        for token, opponent_position in enumerate(opponent_tokens):
            if _ludo_global_cell(state, opponent, opponent_position) == destination:
                state["positions"][opponent][token] = -1
                captured.append(token)
    if captured:
        state["captures"][player] += len(captured)
    return captured


def _apply_ludo_action(
    state: dict[str, Any], player: int, action: dict[str, Any]
) -> dict[str, Any]:
    normalise_ludo_state(state)
    _turn(state, player)
    action_name = action.get("action")

    if action_name == "roll":
        if state["phase"] != "roll":
            raise IllegalMove("Choose a highlighted token before rolling again")
        roll = _roll_die()
        state["action_count"] += 1
        state["roll"] = roll
        state["last_rolls"][player] = roll
        state["six_streak"] = state["six_streak"] + 1 if roll == 6 else 0
        if state["six_streak"] >= 3:
            _ludo_switch_turn(state, "Three sixes ends the turn. The dice passes across.")
            return state
        legal_tokens = _ludo_legal_tokens(state, player, roll)
        state["legal_tokens"] = legal_tokens
        player_name = state["players"][player]["name"]
        if legal_tokens:
            state["phase"] = "move"
            state["last_event"] = f"{player_name} rolled {roll}. Choose a token to move."
        elif roll == 6:
            state["phase"] = "roll"
            state["last_event"] = f"{player_name} rolled 6 but has no legal move. Roll again."
        else:
            _ludo_switch_turn(state, f"{player_name} rolled {roll} with no legal move.")
        return state

    if action_name != "move":
        raise IllegalMove("Roll the dice before choosing a token")
    if state["phase"] != "move" or not isinstance(state.get("roll"), int):
        raise IllegalMove("Roll the dice before choosing a token")
    token = action.get("token")
    if not isinstance(token, int) or token not in state["legal_tokens"]:
        raise IllegalMove("Choose one of the highlighted tokens")

    roll = state["roll"]
    old_position = state["positions"][player][token]
    new_position = 0 if old_position == -1 else old_position + roll
    state["positions"][player][token] = new_position
    captured = _ludo_captures(state, player, new_position)
    finished = new_position == LUDO_FINISH
    state["action_count"] += 1
    state["legal_tokens"] = []
    state["last_move"] = {
        "player": player,
        "token": token,
        "from": old_position,
        "to": new_position,
        "roll": roll,
        "captured": captured,
    }

    player_name = state["players"][player]["name"]
    if all(position == LUDO_FINISH for position in state["positions"][player]):
        state["winner"] = player
        state["phase"] = "finished"
        state["last_event"] = f"{player_name} brought every token home!"
        return state

    event = f"{player_name} moved token {token + 1} by {roll}."
    if captured:
        event += f" Captured {len(captured)} token{'s' if len(captured) != 1 else ''}!"
    if finished:
        event += " One token made it home!"
    extra_turn = roll == 6 or bool(captured) or finished
    if extra_turn:
        state["phase"] = "roll"
        state["last_event"] = event + " Roll again."
    else:
        _ludo_switch_turn(state, event)
    return state


def _bingo_complete(marked: list[list[bool]]) -> bool:
    lines = marked + [[marked[row][col] for row in range(5)] for col in range(5)]
    lines.extend(
        [
            [marked[index][index] for index in range(5)],
            [marked[index][4 - index] for index in range(5)],
        ]
    )
    return any(all(line) for line in lines)


def _domino_sides(tile: list[int], board: list[list[int]]) -> list[str]:
    if not board:
        return ["right"]
    sides: list[str] = []
    if board[0][0] in tile:
        sides.append("left")
    if board[-1][1] in tile:
        sides.append("right")
    return sides


def _domino_legal_moves(state: dict[str, Any], player: int) -> list[dict[str, Any]]:
    return [
        {"tile_index": index, "sides": _domino_sides(tile, state["board"])}
        for index, tile in enumerate(state["hands"][player])
        if _domino_sides(tile, state["board"])
    ]


def _refresh_domino_legal_moves(state: dict[str, Any]) -> None:
    if state.get("winner") is not None or state.get("draw", False):
        state["legal_moves"] = []
        return
    player = int(state["current_player"])
    if state.get("opening_tile_required"):
        state["legal_moves"] = [
            {"tile_index": index, "sides": ["right"]}
            for index, tile in enumerate(state["hands"][player])
            if tile == [6, 6]
        ]
    else:
        state["legal_moves"] = _domino_legal_moves(state, player)


def normalise_domino_state(state: dict[str, Any], player_count: int | None = None) -> None:
    requested_count = max(2, min(4, player_count or len(state.get("hands", [])) or 2))
    old_players = state.get("players", [])
    old_count = len(state.get("hands", []))
    if old_count < requested_count:
        used = {
            tuple(sorted(tile))
            for tile in state.get("board", [])
            + [tile for hand in state.get("hands", []) for tile in hand]
        }
        remaining = [
            [left, right]
            for left in range(7)
            for right in range(left, 7)
            if (left, right) not in used
        ]
        for index in range(old_count, requested_count):
            start = (index - old_count) * 7
            state["hands"].append(remaining[start : start + 7])
    effective_count = len(state.get("hands", [])) or requested_count
    state["player_count"] = effective_count
    state["players"] = _domino_players(effective_count)
    if isinstance(old_players, list):
        for index, old_player in enumerate(old_players[:effective_count]):
            if isinstance(old_player, dict):
                if old_player.get("name"):
                    state["players"][index]["name"] = old_player["name"]
                if "is_bot" in old_player:
                    state["players"][index]["is_bot"] = bool(old_player["is_bot"])
    state.setdefault("passes", 0)
    state.setdefault("turn_number", 1)
    state.setdefault("action_count", 0)
    state.setdefault("last_move", None)
    state.setdefault("round", 1)
    state.setdefault("rounds", 6)
    state.setdefault("round_wins", [0 for _ in range(effective_count)])
    state.setdefault("round_winner", None)
    state.setdefault("starting_player", 0)
    state.setdefault("opening_tile_required", not state.get("board"))
    if state["opening_tile_required"] and not any(
        tile == [6, 6] for hand in state["hands"] for tile in hand
    ):
        state["opening_tile_required"] = False
    state.setdefault("last_event", "Choose a domino that matches either open end.")
    _refresh_domino_legal_moves(state)


def _deal_next_domino_round(state: dict[str, Any], starting_player: int, round_number: int) -> None:
    player_count = int(state["player_count"])
    state["hands"] = _deal_domino_hands(player_count, starting_player, False)
    state["board"] = []
    state["passes"] = 0
    state["current_player"] = starting_player
    state["starting_player"] = starting_player
    state["round"] = round_number
    state["round_winner"] = None
    state["winner"] = None
    state["draw"] = False
    state["opening_tile_required"] = False
    state["last_move"] = None
    _refresh_domino_legal_moves(state)


def _finish_domino_round(state: dict[str, Any], round_winner: int | None) -> None:
    state["round_winner"] = round_winner
    if round_winner is not None:
        state["round_wins"][round_winner] += 1
    round_number = int(state["round"])
    if round_number >= int(state["rounds"]):
        wins = state["round_wins"]
        best = max(wins)
        winners = [index for index, score in enumerate(wins) if score == best]
        state["winner"] = winners[0] if len(winners) == 1 else None
        state["draw"] = len(winners) != 1
        state["last_event"] = (
            f"Six rounds complete. {state['players'][state['winner']]['name']} wins the match."
            if state["winner"] is not None
            else "Six rounds complete. The match is tied."
        )
        _refresh_domino_legal_moves(state)
        return
    next_starter = round_winner if round_winner is not None else int(state["starting_player"])
    _deal_next_domino_round(state, next_starter, round_number + 1)
    state["round_winner"] = round_winner
    state["last_event"] = (
        f"{state['players'][round_winner]['name']} won round {round_number}. "
        f"They lead round {round_number + 1}."
        if round_winner is not None
        else f"Round {round_number} was tied. Round {round_number + 1} begins."
    )


def _finish_blocked_domino_round(state: dict[str, Any]) -> None:
    totals = [sum(sum(tile) for tile in hand) for hand in state["hands"]]
    lowest = min(totals)
    winners = [index for index, total in enumerate(totals) if total == lowest]
    _finish_domino_round(state, winners[0] if len(winners) == 1 else None)


def _apply_domino_action(
    state: dict[str, Any], player: int, action: dict[str, Any]
) -> dict[str, Any]:
    normalise_domino_state(state)
    _turn(state, player)
    legal_moves = _domino_legal_moves(state, player)
    player_name = state["players"][player]["name"]

    if action.get("pass") is True:
        if legal_moves:
            raise IllegalMove("You still have a domino that can be played")
        state["passes"] += 1
        state["action_count"] += 1
        state["last_move"] = {"player": player, "pass": True}
        state["last_event"] = f"{player_name} passed with no legal move."
        if state["passes"] >= state["player_count"]:
            _finish_blocked_domino_round(state)
            return state
        _next_player(state)
        state["turn_number"] += 1
        _refresh_domino_legal_moves(state)
        return state

    index = action.get("tile_index")
    side = action.get("side", "right")
    if not isinstance(index, int) or not 0 <= index < len(state["hands"][player]):
        raise IllegalMove("Choose a domino from your hand")
    if side not in {"left", "right"}:
        raise IllegalMove("Choose the left or right end of the line")
    move = next((move for move in legal_moves if move["tile_index"] == index), None)
    if move is None or side not in move["sides"]:
        raise IllegalMove("That domino does not match this end of the line")

    tile = state["hands"][player].pop(index)
    if not state["board"]:
        oriented = tile
        side = "right"
        state["board"].append(oriented)
    elif side == "left":
        edge = state["board"][0][0]
        oriented = tile if tile[1] == edge else [tile[1], tile[0]]
        state["board"].insert(0, oriented)
    else:
        edge = state["board"][-1][1]
        oriented = tile if tile[0] == edge else [tile[1], tile[0]]
        state["board"].append(oriented)

    state["passes"] = 0
    state["action_count"] += 1
    state["last_move"] = {
        "player": player,
        "tile": oriented,
        "side": side,
        "pass": False,
    }
    state["last_event"] = f"{player_name} placed {oriented[0]}–{oriented[1]} on the {side}."
    if state.get("opening_tile_required"):
        state["opening_tile_required"] = False
    if not state["hands"][player]:
        _finish_domino_round(state, player)
        return state
    _next_player(state)
    state["turn_number"] += 1
    _refresh_domino_legal_moves(state)
    return state


def apply_action(state: dict[str, Any], player: int, action: dict[str, Any]) -> dict[str, Any]:
    if state.get("game") == "csec-it-mock-exam":
        return apply_csec_exam_action(state, player, action)
    if state.get("game") == "together":
        return apply_together_action(state, player, action)
    game = state["game"]
    if action.get("action") == "play_again":
        if state.get("winner") is None and not state.get("draw", False):
            raise IllegalMove("Finish the current game before playing again")
        old_players = state.get("players", [])
        player_count = int(state.get("player_count", len(old_players) or 2))
        bot_players = tuple(index for index, entry in enumerate(old_players) if entry.get("is_bot"))
        replacement = new_state(
            game, player_count, bot_players, state.get("bot_difficulty", "friendly")
        )
        replacement["game_level"] = state.get("game_level", 1)
        replacement["game_streak"] = state.get("game_streak", 0)
        replacement["bot_difficulty"] = state.get("bot_difficulty", "friendly")
        if old_players and replacement.get("players"):
            replacement["players"] = old_players
        for score_key in ("scores", "round_wins"):
            if score_key in state and score_key in replacement:
                replacement[score_key] = list(state[score_key])
        state.clear()
        state.update(replacement)
        return state
    if game == "ludo":
        return _apply_ludo_action(state, player, action)
    if game == "dominoes":
        return _apply_domino_action(state, player, action)
    if game == "bingo":
        if not 0 <= player < len(state.get("cards", [])):
            raise IllegalMove("You are not a player in this round")
        if action.get("action") == "draw":
            if not state["remaining"]:
                state["draw"] = True
                return state
            number = state["remaining"].pop()
            state["drawn"].append(number)
            for card_index, card in enumerate(state["cards"]):
                for row in range(5):
                    for col in range(5):
                        if card[row][col] == number:
                            state["marked_cards"][card_index][row][col] = True
            return state
        if action.get("action") == "claim" and _bingo_complete(state["marked_cards"][player]):
            state["winner"] = player
            return state
        raise IllegalMove("Draw a ball before claiming bingo")
    if game == "scribble":
        return apply_scribble_action(state, player, action)
    if game == "abc-fast-slow":
        if action.get("action") == "next_round":
            return next_abc_round(state)
        return apply_abc_action(state, player, action)
    if game == "checkers":
        return apply_checkers_action(state, player, action)
    return apply_trivia_action(state, player, action)


def bot_action(state: dict[str, Any], player: int) -> dict[str, Any]:
    game = state["game"]
    if game == "trivia":
        return trivia_bot_action(state)
    if game == "ludo":
        normalise_ludo_state(state)
        if state["phase"] == "roll":
            return {"action": "roll"}
        legal_tokens = state.get("legal_tokens", [])
        if not legal_tokens:
            raise IllegalMove("The bot has no legal Ludo move")

        def move_score(token: int) -> tuple[int, int]:
            position = state["positions"][player][token]
            destination = 0 if position == -1 else position + int(state["roll"])
            score = destination
            if destination == LUDO_FINISH:
                score += 1_000
            target_cell = _ludo_global_cell(state, player, destination)
            if target_cell is not None and target_cell not in LUDO_SAFE_CELLS:
                if any(
                    _ludo_global_cell(state, opponent, opponent_position) == target_cell
                    for opponent, opponent_tokens in enumerate(state["positions"])
                    if opponent != player
                    for opponent_position in opponent_tokens
                ):
                    score += 500
            if position == -1:
                score += 120
            return score, -token

        token = max(legal_tokens, key=move_score)
        return {"action": "move", "token": token}
    if game == "dominoes":
        normalise_domino_state(state)
        legal_moves = _domino_legal_moves(state, player)
        if legal_moves:
            move = max(
                legal_moves,
                key=lambda candidate: (
                    sum(state["hands"][player][candidate["tile_index"]]),
                    state["hands"][player][candidate["tile_index"]][0]
                    == state["hands"][player][candidate["tile_index"]][1],
                ),
            )
            return {
                "tile_index": move["tile_index"],
                "side": move["sides"][0],
            }
        return {"pass": True}
    if game == "bingo":
        return {"action": "draw"}
    if game == "scribble":
        return bot_draw_action(state)
    if game == "abc-fast-slow":
        return abc_bot_action(state, player)
    if game == "checkers":
        normalise_checkers_state(state)
        return checkers_bot_action(
            state,
            player,
            state.get("bot_difficulty", "friendly"),
            int(state.get("game_level", 1)),
        )
    return {"answer": state["correct"] if _RNG.random() > 0.35 else _RNG.randrange(4)}
