"""Compact authoritative state machine for the Together co-op game."""

from __future__ import annotations

from typing import Any

from app.games.connect_four import IllegalMove

COLORS = ("#9a7bd3", "#e98a92", "#77aee8", "#7ec7a2", "#e0b65e")
PLAYER_WIDTH = 48.0
PLAYER_HEIGHT = 72.0
WORLD_THEMES = ("meadow", "crystal", "sunset", "moonlit")
MECHANICS = (
    "two-buttons",
    "hold-the-door",
    "moving-platform",
    "seesaw",
    "dont-fall",
    "color-code",
    "elevator",
    "laser-room",
    "dont-press-it",
    "tethered",
    "split-path",
    "fan",
    "crumbling-floor",
    "ice",
    "carry-it",
    "dark-room",
    "falling-platforms",
    "trust-fall",
    "chaos-room",
    "together",
)
LEVELS = tuple(
    {
        "id": index + 1,
        "name": name.replace("-", " ").title(),
        "mechanic": name,
        "width": 1800 + (index % 4) * 300,
        "checkpoint": 650 + (index % 3) * 350,
        "finish": 1550 + (index % 4) * 250,
        "theme": WORLD_THEMES[index // 5],
        "platforms": [
            {"x": 420 + (index % 3) * 60, "y": 100 + (index % 2) * 45, "width": 220, "height": 24},
            {"x": 840 + (index % 4) * 55, "y": 150 + (index % 3) * 35, "width": 190, "height": 24},
            {"x": 1210 + (index % 2) * 80, "y": 95 + (index % 4) * 30, "width": 230, "height": 24},
        ],
        "collectibles": [
            {"x": 320 + index * 18, "y": 82 + (index % 2) * 34},
            {"x": 560 + index * 22, "y": 148 + (index % 3) * 28},
            {"x": 930 + index * 16, "y": 104 + (index % 4) * 26},
            {"x": 1320 + index * 12, "y": 88 + (index % 3) * 38},
        ],
        "plates": [
            {"x": 250 + (index % 2) * 120, "label": "A"},
            {"x": 470 + (index % 3) * 120, "label": "B"},
        ],
        "moving_platforms": [
            {"x": 740 + (index % 3) * 90, "y": 210 + (index % 2) * 32, "width": 150, "range": 90}
        ] if index >= 2 else [],
        "hazards": [
            {"x": 720 + (index % 2) * 90, "width": 120},
            {"x": 1090 + (index % 3) * 60, "width": 100},
        ],
        "cooperation": (
            "Stand on both buttons" if name == "two-buttons" else "Coordinate your timing"
        ),
    }
    for index, name in enumerate(MECHANICS)
)


def level_config(level: int) -> dict[str, Any]:
    return dict(LEVELS[max(1, min(len(LEVELS), level)) - 1])


def _platform_support(
    level: dict[str, Any], x: float, previous_y: float, next_y: float
) -> float | None:
    """Return the highest platform crossed while falling this simulation step."""
    supports = [0.0]
    for platform in level.get("platforms", []):
        left = float(platform["x"]) - float(platform["width"]) / 2
        right = float(platform["x"]) + float(platform["width"]) / 2
        top = float(platform["y"])
        if left <= x <= right and previous_y >= top >= next_y:
            supports.append(top)
    return max(supports) if len(supports) > 1 else (0.0 if next_y <= 0 else None)


def _player_support(
    players: list[dict[str, Any]], current_index: int, x: float, previous_y: float, next_y: float
) -> float | None:
    """Return the highest player top crossed while falling this simulation step."""
    supports: list[float] = []
    half_width = PLAYER_WIDTH / 2
    for index, other in enumerate(players):
        if index == current_index:
            continue
        other_x = float(other.get("x", 0))
        other_y = float(other.get("y", 0))
        if abs(x - other_x) <= half_width * 2:
            other_top = other_y + PLAYER_HEIGHT
            if previous_y >= other_top >= next_y:
                supports.append(other_top)
    return max(supports) if supports else None


def _resolve_player_horizontal(
    players: list[dict[str, Any]], current_index: int, previous_x: float, next_x: float, y: float
) -> float:
    """Prevent block robots from passing through one another on the same tier."""
    current_top = y + PLAYER_HEIGHT
    resolved_x = next_x
    for index, other in enumerate(players):
        if index == current_index:
            continue
        other_x = float(other.get("x", 0))
        other_y = float(other.get("y", 0))
        if not (y < other_y + PLAYER_HEIGHT and current_top > other_y):
            continue
        if abs(resolved_x - other_x) > PLAYER_WIDTH:
            continue
        if next_x > previous_x:
            resolved_x = min(resolved_x, other_x - PLAYER_WIDTH)
        elif next_x < previous_x:
            resolved_x = max(resolved_x, other_x + PLAYER_WIDTH)
    return resolved_x


def new_together_state(
    player_count: int, player_names: dict[int, str] | None = None
) -> dict[str, Any]:
    count = max(1, min(5, player_count))
    names = player_names or {}
    return {
        "game": "together",
        "world": "The Beginning",
        "phase": "playing",
        "level": 1,
        "levels_total": len(LEVELS),
        "player_count": count,
        "players": [
            {
                "name": names.get(seat, f"Player {seat + 1}"),
                "color": COLORS[seat],
                "x": 150 + seat * 52,
                "y": 0,
                "vy": 0,
                "on_ground": True,
                "coyote": 0,
                "jump_buffer": 0,
                "vx": 0,
                "checkpoint": 150,
                "connected": True,
                "falls": 0,
                "is_bot": False,
            }
            for seat in range(count)
        ],
        "level_config": level_config(1),
        "switches": [False] * count,
        "checkpoint_reached": False,
        "finishers": [],
        "falls": 0,
        "restarts": 0,
        "levels_completed": 0,
        "completed_levels": [],
        "winner": None,
        "draw": False,
        "sequence": 0,
        "last_event": "Stay close. Nobody makes it alone.",
    }


def apply_together_action(
    state: dict[str, Any], seat: int, payload: dict[str, Any]
) -> dict[str, Any]:
    if state.get("phase") == "complete":
        raise IllegalMove("The world is already complete")
    try:
        player = state["players"][seat]
    except (IndexError, KeyError):
        raise IllegalMove("Unknown player seat") from None
    action = str(payload.get("action", ""))
    state["sequence"] = int(state.get("sequence", 0)) + 1
    if action == "input":
        axis = max(-1.0, min(1.0, float(payload.get("axis", 0))))
        dt = max(0.01, min(0.12, float(payload.get("dt", 1 / 15))))
        player["vx"] = round(axis * 280, 2)
        previous_x = float(player.get("x", 0))
        player["x"] = round(
            max(50, min(state["level_config"]["width"] - 50, previous_x + player["vx"] * dt)), 2
        )
        player["coyote"] = max(0, float(player.get("coyote", 0)) - dt)
        player["jump_buffer"] = max(0, float(player.get("jump_buffer", 0)) - dt)
        if payload.get("jump"):
            player["jump_buffer"] = 0.12
        if player["jump_buffer"] > 0 and (player["on_ground"] or player["coyote"] > 0):
            player["vy"] = 660
            player["on_ground"], player["coyote"], player["jump_buffer"] = False, 0, 0
        previous_y = float(player.get("y", 0))
        player["vy"] = round(float(player.get("vy", 0)) - 1750 * dt, 2)
        next_y = round(previous_y + player["vy"] * dt, 2)
        player["x"] = round(
            max(
                50,
                min(
                    state["level_config"]["width"] - 50,
                    _resolve_player_horizontal(
                        state["players"], seat, previous_x, player["x"], previous_y
                    ),
                ),
            ),
            2,
        )
        support = _platform_support(state["level_config"], player["x"], previous_y, next_y)
        player_support = _player_support(state["players"], seat, player["x"], previous_y, next_y)
        if player_support is not None:
            support = max(support if support is not None else float("-inf"), player_support)
        if support == float("-inf"):
            support = None
        if support is not None:
            player["y"], player["vy"], player["on_ground"] = support, 0, True
        else:
            player["y"], player["on_ground"] = next_y, False
            if previous_y <= 40 and player["vy"] < 0:
                player["coyote"] = 0.1
        if player["x"] >= state["level_config"]["checkpoint"] and not state["checkpoint_reached"]:
            state["checkpoint_reached"] = True
            for item in state["players"]:
                item["checkpoint"] = state["level_config"]["checkpoint"]
            state["last_event"] = "Checkpoint reached — keep going!"
        state["switches"][seat] = player["x"] >= 260
        if player["x"] >= state["level_config"]["finish"] and seat not in state["finishers"]:
            state["finishers"].append(seat)
    elif action == "fall":
        state["falls"] += 1
        player["falls"] = int(player.get("falls", 0)) + 1
        player["x"], player["y"], player["vy"], player["on_ground"] = (
            player["checkpoint"],
            0,
            0,
            True,
        )
        state["last_event"] = f"{player['name']} went boop. Back to the checkpoint!"
    elif action == "reset_puzzle":
        state["restarts"] += 1
        state["switches"] = [False] * state["player_count"]
        state["last_event"] = "Puzzle reset. Try a new plan together."
    elif action == "finish":
        if len(state["finishers"]) < state["player_count"]:
            raise IllegalMove("Everyone must reach the finish zone")
        state["levels_completed"] += 1
        state["completed_levels"].append(state["level"])
        if state["level"] >= len(LEVELS):
            state["phase"], state["winner"] = "complete", 0
            state["last_event"] = "WE MADE IT!"
        else:
            state["level"] += 1
            state["level_config"] = level_config(state["level"])
            state["switches"] = [False] * state["player_count"]
            state["finishers"], state["checkpoint_reached"] = [], False
            for index, item in enumerate(state["players"]):
                item.update(x=150 + index * 52, y=0, vy=0, on_ground=True, checkpoint=150)
            state["last_event"] = f"Level {state['level']}: {state['level_config']['name']}"
    else:
        raise IllegalMove("That Together action is not available")
    return state


def together_public_event(state: dict[str, Any]) -> dict[str, Any]:
    return {
        "sequence": state["sequence"],
        "state": {
            "level": state["level"],
            "phase": state["phase"],
            "players": state["players"],
            "levels_total": state["levels_total"],
            "level_config": state["level_config"],
            "switches": state["switches"],
            "finishers": state["finishers"],
            "checkpoint_reached": state["checkpoint_reached"],
            "last_event": state["last_event"],
            "levels_completed": state["levels_completed"],
            "falls": state["falls"],
        },
    }
