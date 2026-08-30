import asyncio
import hashlib
import io
import logging
import secrets
import time
from collections import Counter
from collections.abc import Iterable
from copy import deepcopy
from datetime import UTC, date, datetime, timedelta
from html import escape
from pathlib import Path
from typing import Annotated, Any
from uuid import uuid4
from zoneinfo import ZoneInfo

import cloudinary
import cloudinary.uploader
from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    Response,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from fastapi.responses import RedirectResponse
from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy import and_, delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import get_session, session_factory
from app.email_service import send_transactional_email
from app.games.connect_four import ConnectFourState, IllegalMove
from app.games.manager import LiveMatch, match_manager
from app.games.multi import (
    GAME_TYPES,
    normalise_bingo_state,
    normalise_checkers_state,
    normalise_domino_state,
    normalise_ludo_state,
)
from app.games.persistence import create_persisted_match, record_state
from app.games.realtime import realtime_bus
from app.games.scribble import normalise_scribble_state
from app.games.trivia import normalise_trivia_state
from app.games.universal import UniversalMatch, universal_matches
from app.models import (
    Announcement,
    BugReport,
    Challenge,
    ChallengeCompletion,
    CheckIn,
    Comment,
    CommunityApplication,
    Game,
    GameMatch,
    GameMatchPlayer,
    GameProgress,
    GameRoom,
    GameWinner,
    Post,
    PostReaction,
    Quote,
    RewardLedger,
    RoomParticipant,
    SavedQuote,
    Session,
    User,
)
from app.notification_templates import (
    DAILY_CHECKIN_MESSAGES,
    daily_checkin_email,
    weekly_performers_email,
)
from app.oauth import (
    GoogleOAuthError,
    build_google_authorize_url,
    create_oauth_state,
    exchange_google_code,
    frontend_oauth_redirect,
    google_oauth_configured,
    verify_oauth_state,
)
from app.schemas import (
    AdminDashboardResponse,
    AdminNotificationResponse,
    AdminNotificationResult,
    AdminPasswordResetRequest,
    AdminQuoteCreateRequest,
    AdminQuoteUpdateRequest,
    AdminUserUpdateRequest,
    AnnouncementCreateRequest,
    AnnouncementResponse,
    AuthResponse,
    BugReportCreateRequest,
    BugReportResponse,
    BugReportUpdateRequest,
    ChallengeCompleteRequest,
    ChallengeResponse,
    ChallengesResponse,
    ChangePasswordRequest,
    CheckInRequest,
    AbcRoomSettingsRequest,
    CheckInResponse,
    CommentCreateRequest,
    CommentResponse,
    CommentUpdateRequest,
    CommunityApplicationCreateRequest,
    CommunityApplicationResponse,
    CommunityApplicationUpdateRequest,
    CommunityModerationRequest,
    DashboardResponse,
    GameActionRequest,
    GameResponse,
    GameSessionCreateRequest,
    GameSessionResponse,
    GoogleAuthStatusResponse,
    GuestRoomJoinRequest,
    GuestRoomJoinResponse,
    LeaderboardEntry,
    LoginRequest,
    MatchCreateRequest,
    MatchResponse,
    MoveRequest,
    PostCreateRequest,
    PostResponse,
    PostUpdateRequest,
    ProfileUpdateRequest,
    QuoteResponse,
    QuoteSubmissionRequest,
    ReactionRequest,
    RegisterRequest,
    RoomCleanupResponse,
    RoomCreateRequest,
    RoomGameChangeRequest,
    RoomInviteResponse,
    RoomParticipantResponse,
    RoomResponse,
    UserResponse,
)
from app.security import (
    get_current_admin,
    get_current_user,
    hash_password,
    new_session_token,
    session_expiry,
    verify_password,
)

router = APIRouter(prefix="/api", tags=["application"])
logger = logging.getLogger("safe_space_saturdays.games")
DbSession = Annotated[AsyncSession, Depends(get_session)]
CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentAdmin = Annotated[User, Depends(get_current_admin)]

STAFF_ROLES = {"admin", "super_admin", "manager", "moderator"}

DAILY_CHECKIN_QUESTIONS = (
    "What would help this week feel a little more supportive?",
    "What is one thing you want to carry gently into today?",
    "Where did you notice a small win, even if it felt ordinary?",
    "What feeling deserves a little more space today?",
    "What kind of support would help you feel less alone today?",
    "What are you looking forward to, even just a little?",
    "What can you celebrate or gently release from this week?",
)


def daily_checkin_question(current_date: date | None = None) -> str:
    day = current_date or date.today()
    sunday_index = (day.weekday() + 1) % 7
    return DAILY_CHECKIN_QUESTIONS[sunday_index]


def leaderboard_period_start(period: str, now: datetime | None = None) -> datetime:
    """Return the inclusive UTC start of a leaderboard period.

    The weekly leaderboard is calendar-based: Sunday starts a new week. Using
    a rolling seven-day window made a user's "This Week" score change at an
    unexpected time and meant it did not reset consistently for everyone.
    """
    current = now or datetime.now(UTC)
    current = current.astimezone(UTC)
    today = current.date()
    if period == "day":
        start_date = today
    elif period == "week":
        # Python weekday(): Monday=0 ... Sunday=6.
        start_date = today - timedelta(days=(today.weekday() + 1) % 7)
    elif period == "month":
        start_date = today.replace(day=1)
    else:
        raise ValueError(f"Unsupported leaderboard period: {period}")
    return datetime.combine(start_date, datetime.min.time(), tzinfo=UTC)
GOOGLE_OAUTH_COOKIE = "safe_space_google_oauth"
GOOGLE_MOBILE_COOKIE = "safe_space_google_mobile"


def can_manage_roles(user: User) -> bool:
    return user.role in {"admin", "super_admin"}


def can_access_csec_exam(user: User) -> bool:
    """Keep the teacher-created exam private to its two named testers."""
    return user.name.strip().casefold() in {"kashi miller", "tyrese"}


def can_manage_content(user: User) -> bool:
    return user.role in {"admin", "super_admin", "manager"}


def can_moderate_community(user: User) -> bool:
    return user.role in STAFF_ROLES


def ensure_can_post(user: User) -> None:
    now = datetime.now(UTC)
    if user.posting_timeout_until and user.posting_timeout_until > now:
        remaining = int((user.posting_timeout_until - now).total_seconds() // 60) + 1
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail=f"Posting is paused for another {remaining} minute(s).",
        )


def can_review_community_applications(user: User) -> bool:
    return user.role in {"admin", "super_admin", "manager"}


def community_application_response(application: CommunityApplication) -> CommunityApplicationResponse:
    return CommunityApplicationResponse.model_validate(application)


def invite_token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


async def send_application_invite(application: CommunityApplication, token: str) -> bool:
    settings = get_settings()
    invite_url = f"{settings.public_app_url.rstrip('/')}/api/community-applications/invite/{token}"
    safe_name = escape(application.name)
    safe_invite_url = escape(invite_url, quote=True)
    logo_url = escape(f"{settings.public_app_url.rstrip('/')}/assets/safe-space-saturdays-logo.jpeg", quote=True)
    html = f"""<!doctype html>
<html lang="en">
  <head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>Your Safe Space invitation</title></head>
  <body style="margin:0;background:#f4eee7;color:#19352b;font-family:Arial,Helvetica,sans-serif;">
    <div style="display:none;max-height:0;overflow:hidden;opacity:0;">Your Safe Space Saturdays community invitation is ready.</div>
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f4eee7;padding:32px 12px;">
      <tr><td align="center">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:600px;background:#fffdf8;border:1px solid #ddd6c9;border-radius:20px;overflow:hidden;">
          <tr><td style="height:8px;background:#7a8c69;font-size:0;line-height:0;">&nbsp;</td></tr>
          <tr><td align="center" style="padding:30px 28px 18px;">
            <img src="{logo_url}" width="130" alt="Safe Space Saturdays" style="display:block;width:130px;height:auto;border:0;">
          </td></tr>
          <tr><td style="padding:8px 42px 36px;">
            <p style="margin:0 0 12px;color:#7a8c69;font-size:12px;font-weight:bold;letter-spacing:2px;text-transform:uppercase;">You belong here</p>
            <h1 style="margin:0 0 18px;color:#19352b;font-family:Georgia,'Times New Roman',serif;font-size:32px;line-height:1.18;font-weight:700;">Your invitation is ready, {safe_name}.</h1>
            <p style="margin:0 0 18px;color:#59645d;font-size:16px;line-height:1.65;">Your application to join the Safe Space Saturdays community has been approved. We’re looking forward to welcoming you into a kind, supportive circle.</p>
            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin:26px 0;">
              <tr><td align="center" style="border-radius:12px;background:#d87958;">
                <a href="{safe_invite_url}" style="display:inline-block;padding:15px 26px;border:1px solid #d87958;border-radius:12px;color:#fffdf8;font-size:16px;font-weight:bold;text-decoration:none;">Join the WhatsApp community</a>
              </td></tr>
            </table>
            <p style="margin:0 0 8px;color:#7b857d;font-size:13px;line-height:1.55;"><strong style="color:#59645d;">A quick note:</strong> This private invitation expires in 7 days and can only be used once.</p>
            <p style="margin:20px 0 0;color:#9a9f99;font-size:12px;line-height:1.55;">If the button doesn’t work, copy and paste this link into your browser:<br><a href="{safe_invite_url}" style="color:#6b805b;word-break:break-all;">{safe_invite_url}</a></p>
          </td></tr>
          <tr><td style="padding:20px 42px;background:#edf1e7;border-top:1px solid #dfe5d8;color:#6d776e;font-size:12px;line-height:1.55;">Safe Space Saturdays<br>Talk. Listen. Support. Heal. Grow.<br><span style="color:#9a9f99;">You are not alone.</span></td></tr>
        </table>
      </td></tr>
    </table>
  </body>
</html>"""
    text = (
        f"Hi {application.name},\n\nYour Safe Space Saturdays application was approved. "
        f"Join the WhatsApp community here: {invite_url}\n\n"
        "This private invite expires in 7 days and can be used once.\n\n"
        "Safe Space Saturdays — Talk. Listen. Support. Heal. Grow."
    )
    return await send_transactional_email(
        recipient=application.email,
        subject="Your Safe Space Saturdays invitation",
        html=html,
        text=text,
    )


async def notify_admins_of_application(
    application: CommunityApplication, db: AsyncSession
) -> None:
    admins = (
        await db.scalars(
            select(User).where(
                User.role.in_(("admin", "super_admin")),
                User.is_approved.is_(True),
                User.is_guest.is_(False),
                User.email_notifications_enabled.is_(True),
            )
        )
    ).all()
    settings = get_settings()
    admin_url = f"{settings.public_app_url.rstrip('/')}/admin"
    safe_name = escape(application.name)
    safe_message = escape(application.message).replace("\n", "<br>")
    safe_admin_url = escape(admin_url, quote=True)
    html = f"""<!doctype html>
<html lang="en"><body style="margin:0;background:#f4eee7;color:#19352b;font-family:Arial,Helvetica,sans-serif;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="padding:28px 12px;background:#f4eee7;"><tr><td align="center">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:580px;background:#fffdf8;border:1px solid #ddd6c9;border-radius:18px;overflow:hidden;">
      <tr><td style="height:7px;background:#7a8c69;font-size:0;">&nbsp;</td></tr>
      <tr><td style="padding:30px 34px 34px;">
        <p style="margin:0 0 10px;color:#7a8c69;font-size:12px;font-weight:bold;letter-spacing:2px;text-transform:uppercase;">Admin notification</p>
        <h1 style="margin:0 0 16px;font-family:Georgia,serif;font-size:29px;line-height:1.2;">A new community application needs review.</h1>
        <p style="margin:0 0 20px;color:#59645d;font-size:16px;line-height:1.6;"><strong>{safe_name}</strong> has asked to join Safe Space Saturdays.</p>
        <div style="margin:0 0 24px;padding:16px;border-radius:12px;background:#edf1e7;color:#59645d;font-size:14px;line-height:1.6;"><strong style="color:#19352b;">Applicant note</strong><br>{safe_message}</div>
        <a href="{safe_admin_url}" style="display:inline-block;padding:14px 22px;border-radius:11px;background:#d87958;color:#fffdf8;font-size:15px;font-weight:bold;text-decoration:none;">Review application</a>
        <p style="margin:22px 0 0;color:#9a9f99;font-size:12px;line-height:1.5;">This notification was sent to approved Safe Space Saturdays administrators.</p>
      </td></tr>
    </table>
  </td></tr></table>
</body></html>"""
    text = (
        f"A new community application needs review.\n\n{application.name} "
        f"({application.email}) wrote:\n{application.message}\n\nReview it here: {admin_url}"
    )
    await asyncio.gather(
        *(
            send_transactional_email(
                recipient=admin.email,
                subject="New Safe Space Saturdays application to review",
                html=html,
                text=text,
            )
            for admin in admins
        ),
        return_exceptions=True,
    )


def match_response(
    match: LiveMatch, user_id: int | None = None, spectator: bool = False
) -> MatchResponse:
    response = MatchResponse.model_validate(match.snapshot(user_id))
    response.spectator = spectator
    response.spectator_count = match.spectator_count()
    return response


def universal_response(
    match: UniversalMatch, user_id: int | None = None, spectator: bool = False,
    exam_admin: bool = False,
) -> GameSessionResponse:
    response = GameSessionResponse.model_validate(
        match.snapshot(user_id, spectator=spectator, exam_admin=exam_admin)
    )
    response.spectator = spectator
    response.spectator_count = match.spectator_count()
    return response


async def broadcast_spectator_count(match: LiveMatch | UniversalMatch) -> None:
    count = match.spectator_count()
    disconnected: list[WebSocket] = []
    for socket in list(match.sockets):
        try:
            await socket.send_json({"type": "spectator_count", "spectator_count": count})
        except Exception:
            disconnected.append(socket)
    for socket in disconnected:
        match.sockets.pop(socket, None)


def match_channel(match_id: str) -> str:
    return f"safe-space:game:{match_id}"


def restore_connect_match(row: GameMatch, seats: list[GameMatchPlayer] | None = None) -> LiveMatch:
    snapshot = row.state
    raw_last_move = snapshot.get("last_move")
    last_move = (
        (int(raw_last_move[0]), int(raw_last_move[1]))
        if isinstance(raw_last_move, list) and len(raw_last_move) == 2
        else None
    )
    winning_cells = tuple(
        (int(cell[0]), int(cell[1]))
        for cell in snapshot.get("winning_cells", [])
        if isinstance(cell, list) and len(cell) == 2
    )
    state = ConnectFourState(
        board=tuple(tuple(int(cell) for cell in board_row) for board_row in snapshot["board"]),
        current_player=1 if int(snapshot["current_player"]) == 1 else 2,
        winner=snapshot.get("winner"),
        draw=bool(snapshot.get("draw", False)),
        move_count=int(snapshot.get("move_count", 0)),
        last_move=last_move,
        winning_cells=winning_cells,
    )
    seat_rows = seats or []
    player_ids = {
        seat.user_id: seat.seat_index + 1 for seat in seat_rows if seat.user_id is not None
    } or {row.player_user_id: 1}
    bot_player = next(
        (seat.seat_index + 1 for seat in seat_rows if seat.player_type == "bot"), None
    )
    match = LiveMatch(
        id=row.id,
        room_id=row.room_id,
        state=state,
        player_ids=player_ids,
        bot_player=bot_player,
        players=[
            {
                "name": seat.display_name,
                "is_bot": seat.player_type == "bot",
            }
            for seat in seat_rows
        ] or [{"name": "You", "is_bot": False}, {"name": "Milo Bot", "is_bot": True}],
        version=row.version,
    )
    match_manager.matches[row.id] = match
    match_manager.room_matches[row.room_id] = row.id
    return match


def restore_universal_match(
    row: GameMatch, player_count: int = 2, seats: list[GameMatchPlayer] | None = None
) -> UniversalMatch:
    if row.game_type == "ludo":
        normalise_ludo_state(row.state, player_count)
    if row.game_type == "dominoes":
        normalise_domino_state(row.state, player_count)
    if row.game_type == "trivia":
        normalise_trivia_state(row.state)
    if row.game_type == "bingo":
        normalise_bingo_state(row.state, player_count)
    if row.game_type == "scribble":
        normalise_scribble_state(row.state)
    if row.game_type == "checkers":
        normalise_checkers_state(row.state)
    seat_rows = seats or []
    player_ids = {
        seat.user_id: seat.seat_index for seat in seat_rows if seat.user_id is not None
    } or {row.player_user_id: 0}
    bot_players = tuple(seat.seat_index for seat in seat_rows if seat.player_type == "bot")
    # Hydration normalises older saved state, so restore the authoritative seat
    # metadata afterwards. Without this, a second human is renamed to a bot in
    # Ludo as soon as the match is loaded from PostgreSQL.
    state_players = row.state.get("players", [])
    if isinstance(state_players, list):
        for seat in seat_rows:
            if 0 <= seat.seat_index < len(state_players) and isinstance(state_players[seat.seat_index], dict):
                state_players[seat.seat_index]["name"] = seat.display_name
                state_players[seat.seat_index]["is_bot"] = seat.player_type == "bot"
    resolved_bot_players = bot_players if seat_rows else tuple(
        range(1, player_count if row.game_type in {"ludo", "dominoes", "scribble", "abc-fast-slow"} else 2)
    )
    match = UniversalMatch(
        id=row.id,
        room_id=row.room_id,
        game_type=row.game_type,
        state=row.state,
        player_ids=player_ids,
        bot_player=resolved_bot_players[0] if resolved_bot_players else None,
        bot_players=resolved_bot_players,
        version=row.version,
    )
    universal_matches.matches[row.id] = match
    return match


async def hydrate_match(match_id: str) -> tuple[LiveMatch | None, UniversalMatch | None]:
    async with session_factory() as db:
        row = await db.get(GameMatch, match_id)
        if row is None:
            return None, None
        seats = list(
            (
                await db.scalars(
                    select(GameMatchPlayer)
                    .where(GameMatchPlayer.match_id == row.id)
                    .order_by(GameMatchPlayer.seat_index)
                )
            ).all()
        )
        if row.game_type == "connect-four":
            return restore_connect_match(row, seats), None
        room = await db.get(GameRoom, row.room_id)
        player_count = (
            room.max_players if room is not None and row.game_type in {"ludo", "dominoes", "scribble"} else 2
        )
        return None, restore_universal_match(row, player_count, seats)


def apply_connect_snapshot(match: LiveMatch, snapshot: dict[str, Any]) -> None:
    raw_last_move = snapshot.get("last_move")
    last_move = (
        (int(raw_last_move[0]), int(raw_last_move[1]))
        if isinstance(raw_last_move, list) and len(raw_last_move) == 2
        else None
    )
    raw_cells = snapshot.get("winning_cells", [])
    winning_cells = tuple(
        (int(cell[0]), int(cell[1]))
        for cell in raw_cells
        if isinstance(cell, list) and len(cell) == 2
    ) if isinstance(raw_cells, list) else ()
    board = snapshot.get("board")
    if not isinstance(board, list):
        raise ValueError("Connect Four update has no board")
    match.state = ConnectFourState(
        board=tuple(tuple(int(cell) for cell in row) for row in board),
        current_player=1 if int(snapshot.get("current_player", 1)) == 1 else 2,
        winner=snapshot.get("winner"),
        draw=bool(snapshot.get("draw", False)),
        move_count=int(snapshot.get("move_count", 0)),
        last_move=last_move,
        winning_cells=winning_cells,
    )


async def relay_remote_events(
    websocket: WebSocket, match: LiveMatch, user_id: int, spectator: bool
) -> None:
    async for message in realtime_bus.subscribe(match_channel(match.id)):
        if message.get("origin") != get_settings().realtime_node_id:
            payload = message.get("payload")
            if not isinstance(payload, dict):
                continue
            if payload.get("type") == "state" and isinstance(payload.get("state"), dict):
                version = int(payload.get("version", 0))
                async with match.lock:
                    if version >= match.version:
                        apply_connect_snapshot(match, payload["state"])
                        match.version = version
                await websocket.send_json(
                    {
                        "type": "state",
                        "state": {
                            **match.snapshot(None if spectator else user_id),
                            "spectator": spectator,
                        },
                    }
                )
            else:
                await websocket.send_json(payload)


async def relay_remote_universal_events(
    websocket: WebSocket, match: UniversalMatch, user_id: int
) -> None:
    async for message in realtime_bus.subscribe(match_channel(match.id)):
        if message.get("origin") != get_settings().realtime_node_id:
            payload = message.get("payload")
            if not isinstance(payload, dict):
                continue
            if payload.get("type") == "state" and isinstance(payload.get("state"), dict):
                version = int(payload.get("version", 0))
                async with match.lock:
                    if version >= match.version:
                        match.state = deepcopy(payload["state"])
                        match.version = version
                await websocket.send_json({"type": "state", "match": match.snapshot(user_id)})
            else:
                await websocket.send_json(payload)


async def grant_game_reward(
    db: AsyncSession, user_id: int, match_id: str, kind: str, xp: int
) -> bool:
    key = f"game-{kind}:{match_id}:{user_id}"
    existing = await db.scalar(select(RewardLedger).where(RewardLedger.idempotency_key == key))
    if existing is not None:
        return False
    user = await db.get(User, user_id)
    if user is None:
        return False
    user.xp += xp
    user.level = max(1, user.xp // 250 + 1)
    db.add(
        RewardLedger(
            user_id=user_id,
            match_id=match_id,
            kind=f"game_{kind}",
            xp=xp,
            idempotency_key=key,
        )
    )
    return True


async def grant_game_participation_reward(db: AsyncSession, user_id: int, match_id: str) -> bool:
    return await grant_game_reward(db, user_id, match_id, "participation", 5)


async def grant_game_win_reward(db: AsyncSession, user_id: int, match_id: str) -> bool:
    return await grant_game_reward(db, user_id, match_id, "win", 10)


def record_game_progress_result(progress: GameProgress, won: bool) -> None:
    if won:
        progress.wins += 1
        progress.current_streak += 1
        progress.best_streak = max(progress.best_streak, progress.current_streak)
        # Every win is a visible level-up; level 1 is the starting level.
        progress.level = progress.wins + 1
    else:
        progress.current_streak = 0


async def grant_completed_game_rewards(
    db: AsyncSession,
    player_ids: dict[int, int],
    match_id: str,
    winner: int | None,
) -> dict[int, GameProgress]:
    """Reconcile rewards for every human when a match reaches a terminal state."""
    match = await db.get(GameMatch, match_id)
    for user_id, seat in player_ids.items():
        await grant_game_participation_reward(db, user_id, match_id)
        if match is not None and match.game_type == "together":
            await grant_game_reward(db, user_id, match_id, "together-world", 50)
            await grant_game_reward(db, user_id, match_id, "together-team", 10)
        elif winner is not None and seat == winner:
            await grant_game_win_reward(db, user_id, match_id)
    if match is None:
        return {}
    updated: dict[int, GameProgress] = {}
    for user_id, seat in player_ids.items():
        progress = await db.scalar(select(GameProgress).where(
            GameProgress.user_id == user_id, GameProgress.game_type == match.game_type
        ))
        if progress is None:
            # ORM defaults are applied during INSERT, but progression is
            # incremented before the first flush. Initialize the in-memory row
            # so a player's first win cannot attempt arithmetic on None.
            progress = GameProgress(
                user_id=user_id,
                game_type=match.game_type,
                wins=0,
                current_streak=0,
                best_streak=0,
                level=1,
            )
            db.add(progress)
        if winner is not None:
            record_game_progress_result(progress, match is not None and match.game_type == "together" or seat == winner)
        updated[user_id] = progress
    return updated


def apply_progress_to_live_match(
    match: LiveMatch | UniversalMatch,
    user_id: int,
    progress_by_user: dict[int, GameProgress],
) -> None:
    progress = progress_by_user.get(user_id)
    if progress is None:
        return
    if isinstance(match, LiveMatch):
        match.game_level = progress.level
        match.game_streak = progress.current_streak
        if progress.level >= 2:
            match.bot_difficulty = "thoughtful"
        return
    match.state["game_level"] = progress.level
    match.state["game_streak"] = progress.current_streak
    if progress.level >= 2:
        match.state["bot_difficulty"] = "thoughtful"


async def settle_completed_match_progress(
    db: AsyncSession,
    match: LiveMatch | UniversalMatch,
    user_id: int,
) -> bool:
    async with match.settlement_lock:
        winner = match.state.winner if isinstance(match, LiveMatch) else match.state.get("winner")
        draw = match.state.draw if isinstance(match, LiveMatch) else match.state.get("draw", False)
        if (winner is None and not draw) or match.reward_granted:
            return False

        # Claim settlement before the first database await. A simultaneous Play
        # again request waits on this lock, then resets from the updated state.
        match.reward_granted = True
        try:
            progress = await grant_completed_game_rewards(
                db, match.player_ids, match.id, winner
            )
        except Exception:
            match.reward_granted = False
            raise
        apply_progress_to_live_match(match, user_id, progress)
        return True


async def grant_community_post_reward(db: AsyncSession, user_id: int, post_id: int) -> bool:
    key = f"community-post:{post_id}:{user_id}"
    existing = await db.scalar(select(RewardLedger).where(RewardLedger.idempotency_key == key))
    if existing is not None:
        return False
    user = await db.get(User, user_id)
    if user is None:
        return False
    user.xp += 5
    user.level = max(1, user.xp // 250 + 1)
    db.add(
        RewardLedger(
            user_id=user_id,
            match_id=None,
            kind="community_post",
            xp=5,
            idempotency_key=key,
        )
    )
    return True


def game_type_for_name(name: str) -> str | None:
    normalized = name.casefold()
    if normalized == "ludo":
        return "ludo"
    if normalized in {"dominoes", "block dominoes"}:
        return "dominoes"
    if normalized == "bingo":
        return "bingo"
    if normalized in {"trivia", "trivia battle"}:
        return "trivia"
    if normalized in {"scribble", "scribble game", "draw and guess"}:
        return "scribble"
    if normalized in {"abc fast or slow", "abc fast/slow", "fast or slow"}:
        return "abc-fast-slow"
    if normalized in {"checkers", "draughts"}:
        return "checkers"
    if normalized in {"together", "linked together"}:
        return "together"
    if normalized in {"csec it mock exam", "csec it exam"}:
        return "csec-it-mock-exam"
    return None


def new_guest_email() -> str:
    return f"guest-{uuid4()}@guests.safespacesaturdays.app"


def is_user_online(user: User) -> bool:
    if user.last_seen_at is None:
        return False
    last_seen = user.last_seen_at
    if last_seen.tzinfo is None:
        last_seen = last_seen.replace(tzinfo=UTC)
    return datetime.now(UTC) - last_seen <= timedelta(minutes=5)


CHALLENGE_TEMPLATES: tuple[dict[str, object], ...] = (
    {
        "slug": "notice-beauty",
        "title": "Notice something beautiful",
        "description": (
            "Pause for a moment and notice a flower, cloud, color, or other small detail "
            "that brings you a little joy."
        ),
        "category": "Notice",
        "icon": "🌼",
        "color": "sage",
        "xp": 10,
    },
    {
        "slug": "kind-word",
        "title": "Offer a kind word",
        "description": (
            "Give someone a sincere compliment, only if it feels welcome and comfortable "
            "for both of you."
        ),
        "category": "Connect",
        "icon": "💬",
        "color": "peach",
        "xp": 15,
    },
    {
        "slug": "screen-free-pause",
        "title": "Take a screen-free pause",
        "description": (
            "Set your phone aside for ten quiet minutes. Breathe, stretch, or simply let "
            "your mind wander."
        ),
        "category": "Restore",
        "icon": "☁️",
        "color": "lilac",
        "xp": 10,
    },
    {
        "slug": "handled-well",
        "title": "Name something you handled well",
        "description": (
            "Write one small thing you navigated this week, even if it felt ordinary or "
            "unfinished."
        ),
        "category": "Reflect",
        "icon": "✍️",
        "color": "blue",
        "xp": 15,
    },
    {
        "slug": "appreciation-note",
        "title": "Send appreciation",
        "description": (
            "Send a short thank-you or appreciation message to someone you trust—or write "
            "one for yourself."
        ),
        "category": "Connect",
        "icon": "💛",
        "color": "coral",
        "xp": 15,
    },
)


def challenge_window(today: date | None = None) -> tuple[date, date]:
    current = today or datetime.now(UTC).date()
    start = current - timedelta(days=current.weekday())
    return start, start + timedelta(days=6)


async def ensure_current_challenges(
    db: AsyncSession, week_start: date, active_until: date
) -> list[Challenge]:
    rows = list(
        (
            await db.scalars(
                select(Challenge)
                .where(Challenge.week_start == week_start)
                .order_by(Challenge.id)
            )
        ).all()
    )
    existing_slugs = {row.slug for row in rows}
    for template in CHALLENGE_TEMPLATES:
        if str(template["slug"]) in existing_slugs:
            continue
        db.add(
            Challenge(
                slug=str(template["slug"]),
                title=str(template["title"]),
                description=str(template["description"]),
                category=str(template["category"]),
                icon=str(template["icon"]),
                color=str(template["color"]),
                xp=int(template["xp"]),
                week_start=week_start,
                active_until=active_until,
            )
        )
    if len(existing_slugs) < len(CHALLENGE_TEMPLATES):
        await db.flush()
        rows = list(
            (
                await db.scalars(
                    select(Challenge)
                    .where(Challenge.week_start == week_start)
                    .order_by(Challenge.id)
                )
            ).all()
        )
    return rows


def challenge_out(
    challenge: Challenge, completion: ChallengeCompletion | None
) -> ChallengeResponse:
    return ChallengeResponse(
        id=challenge.id,
        slug=challenge.slug,
        title=challenge.title,
        description=challenge.description,
        category=challenge.category,
        icon=challenge.icon,
        color=challenge.color,
        xp=challenge.xp,
        week_start=challenge.week_start,
        active_until=challenge.active_until,
        completed=completion is not None,
        completed_at=completion.created_at if completion else None,
        reflection=completion.reflection if completion else None,
    )


def user_response(user: User) -> UserResponse:
    values = {
        **{
            field: (
                getattr(user, field)
                if field != "email_notifications_enabled"
                else (getattr(user, field, None) is not False)
            )
            for field in UserResponse.model_fields
            if field != "is_online"
        },
        "is_online": is_user_online(user),
    }
    if user.is_guest and user.email.endswith("@guest.invalid"):
        values["email"] = f"guest-{user.id}@guests.safespacesaturdays.app"
    return UserResponse.model_validate(values)


def game_capacity(game_name: str) -> int:
    normalized = game_name.strip().lower()
    if normalized in {"connect four", "connect-four", "trivia", "trivia battle", "checkers", "draughts"}:
        return 2
    if normalized in {"ludo", "dominoes", "block dominoes", "scribble", "scribble game"}:
        return 4
    if normalized in {"together", "linked together"}:
        return 5
    if normalized in {"abc fast or slow", "abc fast/slow", "fast or slow"}:
        return 0  # ABC capacity is chosen by the room host.
    if normalized in {"csec it mock exam", "csec it exam"}:
        return 2
    if normalized == "bingo":
        return 8
    return 4


def room_participant_is_ready(room: GameRoom, participant: RoomParticipant) -> bool:
    """Hosts are ready by definition because they control when the match starts."""
    return participant.user_id == room.host_id or participant.ready


async def build_match_seats(
    room: GameRoom,
    game_type: str,
    user_id: int,
    db: AsyncSession,
    fill_with_bots: bool,
) -> tuple[list[dict[str, object]], dict[int, int], tuple[int, ...], dict[int, str]]:
    participants = (
        await db.scalars(
            select(RoomParticipant)
            .where(RoomParticipant.room_id == room.id)
            .order_by(RoomParticipant.joined_at, RoomParticipant.id)
        )
    ).all()
    if not any(participant.user_id == user_id for participant in participants):
        raise HTTPException(status_code=403, detail="Join the room before starting a match")
    if not all(room_participant_is_ready(room, participant) for participant in participants):
        raise HTTPException(status_code=409, detail="Every human player must be ready")
    capacity = game_capacity(game_type)
    count = room.max_players if game_type == "abc-fast-slow" or capacity == 0 else min(room.max_players, capacity)
    if len(participants) > count:
        raise HTTPException(
            status_code=409, detail="This room has too many players for the selected game"
        )
    if game_type not in {"together", "abc-fast-slow"} and not fill_with_bots and len(participants) < count:
        raise HTTPException(
            status_code=409, detail=f"All {count} seats must be filled before starting"
        )
    users = {
        user.id: user
        for user in (
            await db.scalars(
                select(User).where(
                    User.id.in_([participant.user_id for participant in participants])
                )
            )
        ).all()
    }
    bot_names = (
        "Milo Bot",
        "Maya Bot",
        "Sunny Bot",
        "Cedar Bot",
        "River Bot",
        "Sage Bot",
        "Olive Bot",
    )
    seats: list[dict[str, object]] = []
    player_ids: dict[int, int] = {}
    bot_players: list[int] = []
    player_names: dict[int, str] = {}
    seat_count = len(participants) if game_type in {"together", "abc-fast-slow"} and not fill_with_bots else count
    for seat_index in range(seat_count):
        if seat_index < len(participants):
            participant = participants[seat_index]
            member = users[participant.user_id]
            participant.seat_index = seat_index
            player_ids[member.id] = seat_index
            player_names[seat_index] = member.name
            seats.append(
                {
                    "seat_index": seat_index,
                    "user_id": member.id,
                    "player_type": "human",
                    "display_name": member.name,
                    "bot_difficulty": None,
                }
            )
        else:
            bot_players.append(seat_index)
            name = bot_names[seat_index % len(bot_names)]
            player_names[seat_index] = name
            seats.append(
                {
                    "seat_index": seat_index,
                    "user_id": None,
                    "player_type": "bot",
                    "display_name": name,
                    "bot_difficulty": room.bot_difficulty,
                }
            )
    return seats, player_ids, tuple(bot_players), player_names


def bug_report_response(report: BugReport, reporter: User) -> BugReportResponse:
    return BugReportResponse(
        id=report.id,
        user_id=report.user_id,
        reporter_name=reporter.name,
        reporter_email=reporter.email,
        title=report.title,
        description=report.description,
        severity=report.severity,
        status=report.status,
        page_url=report.page_url,
        admin_note=report.admin_note,
        created_at=report.created_at,
        updated_at=report.updated_at,
    )


def current_checkin_streak(checkin_dates: Iterable[date], today: date) -> int:
    dates = sorted(set(checkin_dates), reverse=True)
    if not dates or dates[0] < today - timedelta(days=1):
        return 0
    streak = 1
    expected = dates[0] - timedelta(days=1)
    for checkin_date in dates[1:]:
        if checkin_date != expected:
            break
        streak += 1
        expected -= timedelta(days=1)
    return streak


async def refresh_checkin_streak(user: User, db: AsyncSession) -> None:
    checkin_dates = await db.scalars(
        select(CheckIn.created_at).where(
            CheckIn.user_id == user.id, CheckIn.completed.is_(True)
        )
    )
    dates = [created_at.astimezone(UTC).date() for created_at in checkin_dates if created_at]
    user.streak = current_checkin_streak(dates, date.today())


async def set_session(
    response: Response, db: AsyncSession, user: User, remember_me: bool = True
) -> str:
    user.last_seen_at = datetime.now(UTC)
    token, token_hash = new_session_token()
    db.add(Session(user_id=user.id, token_hash=token_hash, expires_at=session_expiry(remember_me)))
    await db.commit()
    response.set_cookie(
        get_settings().session_cookie_name,
        token,
        httponly=True,
        secure=get_settings().cookie_secure,
        samesite="none" if get_settings().cookie_secure else "lax",
        max_age=60 * 60 * 24 * (get_settings().session_ttl_days if remember_me else 1),
    )
    return token


def clear_google_oauth_cookie(response: Response) -> None:
    response.delete_cookie(GOOGLE_OAUTH_COOKIE, path="/api/auth/google")
    response.delete_cookie(GOOGLE_MOBILE_COOKIE, path="/api/auth/google")


def google_oauth_error_response(error: str) -> RedirectResponse:
    settings = get_settings()
    try:
        target = frontend_oauth_redirect(settings, error)
    except GoogleOAuthError:
        target = "/login"
    response = RedirectResponse(target, status_code=status.HTTP_303_SEE_OTHER)
    clear_google_oauth_cookie(response)
    return response


@router.get("/auth/google/status", response_model=GoogleAuthStatusResponse)
async def google_oauth_status() -> GoogleAuthStatusResponse:
    return GoogleAuthStatusResponse(enabled=google_oauth_configured(get_settings()))


@router.get("/auth/google/start", include_in_schema=False)
async def google_oauth_start(mobile: bool = False) -> RedirectResponse:
    settings = get_settings()
    if not google_oauth_configured(settings):
        raise HTTPException(status_code=503, detail="Google sign-in is not available")
    state_value, nonce, cookie = create_oauth_state(settings)
    response = RedirectResponse(
        build_google_authorize_url(settings, state_value, nonce),
        status_code=status.HTTP_302_FOUND,
    )
    response.set_cookie(
        GOOGLE_OAUTH_COOKIE,
        cookie,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=settings.google_oauth_state_ttl_seconds,
        path="/api/auth/google",
    )
    if mobile:
        response.set_cookie(
            GOOGLE_MOBILE_COOKIE,
            "safespacesaturdays://oauth",
            httponly=True,
            secure=settings.cookie_secure,
            samesite="lax",
            max_age=settings.google_oauth_state_ttl_seconds,
            path="/api/auth/google",
        )
    return response


@router.get("/auth/google/callback", include_in_schema=False)
async def google_oauth_callback(
    request: Request,
    db: DbSession,
    state: str | None = None,
    code: str | None = None,
    error: str | None = None,
) -> RedirectResponse:
    settings = get_settings()
    if not google_oauth_configured(settings):
        return google_oauth_error_response("unavailable")
    try:
        nonce = verify_oauth_state(
            settings,
            request.cookies.get(GOOGLE_OAUTH_COOKIE),
            state,
        )
        if error:
            return google_oauth_error_response("cancelled")
        if not code:
            raise GoogleOAuthError("Missing Google authorization code")
        identity = await exchange_google_code(settings, code, nonce)
    except GoogleOAuthError:
        return google_oauth_error_response("failed")

    user = await db.scalar(select(User).where(User.google_subject == identity.subject))
    if user is None:
        user = await db.scalar(select(User).where(User.email == identity.email))
        if user is not None:
            if user.google_subject and user.google_subject != identity.subject:
                return google_oauth_error_response("account_conflict")
            user.google_subject = identity.subject
            if not user.avatar_url and identity.picture:
                user.avatar_url = identity.picture
        else:
            registered_count = await db.scalar(select(func.count(User.id))) or 0
            user = User(
                name=identity.name[:120],
                email=identity.email,
                password_hash=hash_password(secrets.token_urlsafe(48)),
                google_subject=identity.subject,
                avatar_url=identity.picture,
                level=1,
                # Keep local/test browser journeys deterministic; production
                # retains the approval cap and admin workflow.
                is_approved=registered_count < 20 or get_settings().app_env != "production",
            )
            db.add(user)
            await db.flush()

    if not user.is_approved:
        await db.commit()
        return google_oauth_error_response("pending_approval")

    mobile_redirect = request.cookies.get(GOOGLE_MOBILE_COOKIE)
    if mobile_redirect == "safespacesaturdays://oauth":
        response = RedirectResponse(
            "safespacesaturdays://oauth",
            status_code=status.HTTP_303_SEE_OTHER,
        )
        token = await set_session(response, db, user)
        response.headers["location"] = f"safespacesaturdays://oauth?{urlencode({'token': token})}"
    else:
        response = RedirectResponse(
            frontend_oauth_redirect(settings),
            status_code=status.HTTP_303_SEE_OTHER,
        )
        await set_session(response, db, user)
    clear_google_oauth_cookie(response)
    return response


@router.post("/auth/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, response: Response, db: DbSession) -> AuthResponse:
    email = payload.email.strip().lower()
    existing = await db.scalar(select(User).where(User.email == email))
    if existing:
        raise HTTPException(status_code=409, detail="An account with this email already exists")
    registered_count = await db.scalar(select(func.count(User.id))) or 0
    is_approved = registered_count < 20 or get_settings().app_env != "production"
    user = User(
        name=payload.name.strip(),
        email=email,
        password_hash=hash_password(payload.password),
        level=1,
        is_approved=is_approved,
    )
    db.add(user)
    await db.flush()
    if is_approved:
        token = await set_session(response, db, user)
        return AuthResponse(user=user_response(user), access_token=token)
    await db.commit()
    return AuthResponse(
        user=user_response(user),
        pending_approval=True,
        message="Your account is awaiting approval before you can sign in.",
    )


@router.post("/auth/login", response_model=AuthResponse)
async def login(payload: LoginRequest, response: Response, db: DbSession) -> AuthResponse:
    email = payload.email.strip().lower()
    user = await db.scalar(select(User).where(User.email == email))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.is_approved:
        raise HTTPException(
            status_code=403,
            detail="Your account is awaiting approval before you can sign in",
        )
    token = await set_session(response, db, user, payload.remember_me)
    return AuthResponse(user=user_response(user), access_token=token)


@router.post("/auth/refresh", response_model=AuthResponse)
async def refresh_auth(
    request: Request, response: Response, user: CurrentUser, db: DbSession
) -> AuthResponse:
    """Rotate a valid session token for native clients and long-lived sessions."""
    old_token = request.cookies.get(get_settings().session_cookie_name)
    authorization = request.headers.get("Authorization", "")
    if not old_token and authorization.startswith("Bearer "):
        old_token = authorization[7:]
    if old_token:
        import hashlib

        token_hash = hashlib.sha256(old_token.encode()).hexdigest()
        await db.execute(delete(Session).where(Session.token_hash == token_hash))
        await db.commit()
    token = await set_session(response, db, user, True)
    return AuthResponse(user=user_response(user), access_token=token)


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(request: Request, response: Response, db: DbSession) -> None:
    token = request.cookies.get(get_settings().session_cookie_name)
    authorization = request.headers.get("Authorization", "")
    if not token and authorization.startswith("Bearer "):
        token = authorization[7:]
    if token:
        import hashlib

        await db.execute(
            delete(Session).where(Session.token_hash == hashlib.sha256(token.encode()).hexdigest())
        )
        await db.commit()
    response.delete_cookie(get_settings().session_cookie_name)


@router.get("/auth/me", response_model=UserResponse)
async def me(user: CurrentUser, db: DbSession) -> UserResponse:
    await refresh_checkin_streak(user, db)
    user.last_seen_at = datetime.now(UTC)
    await db.commit()
    return user_response(user)


@router.post("/bug-reports", response_model=BugReportResponse, status_code=status.HTTP_201_CREATED)
async def create_bug_report(
    payload: BugReportCreateRequest, request: Request, user: CurrentUser, db: DbSession
) -> BugReportResponse:
    report = BugReport(
        user_id=user.id,
        title=payload.title.strip(),
        description=payload.description.strip(),
        severity=payload.severity,
        page_url=payload.page_url,
        user_agent=request.headers.get("user-agent"),
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)
    return bug_report_response(report, user)


@router.patch("/auth/me", response_model=UserResponse)
async def update_me(
    payload: ProfileUpdateRequest, user: CurrentUser, db: DbSession
) -> UserResponse:
    user.name = payload.name.strip()
    await db.commit()
    await db.refresh(user)
    return user_response(user)


@router.post("/auth/me/password", status_code=status.HTTP_204_NO_CONTENT)
async def change_my_password(
    payload: ChangePasswordRequest, user: CurrentUser, db: DbSession
) -> None:
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )
    user.password_hash = hash_password(payload.new_password)
    await db.commit()


@router.post("/auth/me/avatar", response_model=UserResponse)
async def update_avatar(
    user: CurrentUser, db: DbSession, image: Annotated[UploadFile, File(...)]
) -> UserResponse:
    user.avatar_url = await save_post_image(image)
    await db.commit()
    await db.refresh(user)
    return user_response(user)


@router.get("/dashboard", response_model=DashboardResponse)
async def dashboard(user: CurrentUser, db: DbSession) -> DashboardResponse:
    await refresh_checkin_streak(user, db)
    latest = await db.scalar(
        select(CheckIn)
        .where(CheckIn.user_id == user.id)
        .order_by(CheckIn.created_at.desc())
        .limit(1)
    )
    # Rotate through the approved library once per calendar day. The ordinal
    # makes the choice stable for everyone during a day without storing a
    # mutable "current quote" row or returning the first featured quote forever.
    approved_quotes = select(Quote).where(Quote.approval_status == "approved").order_by(Quote.id)
    quote_count = await db.scalar(
        select(func.count(Quote.id)).where(Quote.approval_status == "approved")
    ) or 0
    quote = None
    if quote_count:
        quote = await db.scalar(
            approved_quotes.offset(date.today().toordinal() % quote_count).limit(1)
        )
    rank = (
        await db.scalar(
            select(func.count(User.id)).where(User.is_guest.is_(False), User.xp > user.xp)
        )
        or 0
    ) + 1
    quote_response = None if quote is None else QuoteResponse.model_validate(quote)
    checkin_response = None if latest is None else CheckInResponse.model_validate(latest)
    return DashboardResponse(
        user=user_response(user),
        featured_quote=quote_response,
        latest_check_in=checkin_response,
        rank=rank,
        level_progress=min(100, (user.xp % 250) * 100 // 250),
        daily_checkin_question=daily_checkin_question(),
    )


@router.get("/challenges/current", response_model=ChallengesResponse)
async def current_challenges(user: CurrentUser, db: DbSession) -> ChallengesResponse:
    if user.is_guest or not user.is_approved:
        raise HTTPException(status_code=403, detail="Challenges are available to approved members")
    week_start, active_until = challenge_window()
    challenges = await ensure_current_challenges(db, week_start, active_until)
    completions = list(
        (
            await db.scalars(
                select(ChallengeCompletion).where(
                    ChallengeCompletion.user_id == user.id,
                    ChallengeCompletion.challenge_id.in_([
                        challenge.id for challenge in challenges
                    ]),
                )
            )
        ).all()
    )
    by_challenge = {completion.challenge_id: completion for completion in completions}
    await db.commit()
    return ChallengesResponse(
        week_start=week_start,
        active_until=active_until,
        completed_count=len(completions),
        total_count=len(challenges),
        xp_earned=sum(completion.xp_awarded for completion in completions),
        challenges=[
            challenge_out(challenge, by_challenge.get(challenge.id)) for challenge in challenges
        ],
    )


@router.post("/challenges/{challenge_id}/complete", response_model=ChallengeResponse)
async def complete_challenge(
    challenge_id: int,
    payload: ChallengeCompleteRequest,
    user: CurrentUser,
    db: DbSession,
) -> ChallengeResponse:
    if user.is_guest or not user.is_approved:
        raise HTTPException(status_code=403, detail="Challenges are available to approved members")
    week_start, active_until = challenge_window()
    challenge = await db.scalar(
        select(Challenge).where(
            Challenge.id == challenge_id,
            Challenge.week_start == week_start,
            Challenge.active_until >= datetime.now(UTC).date(),
        )
    )
    if challenge is None:
        raise HTTPException(status_code=404, detail="Challenge is no longer available")
    locked_user = await db.scalar(select(User).where(User.id == user.id).with_for_update())
    if locked_user is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    completion = await db.scalar(
        select(ChallengeCompletion).where(
            ChallengeCompletion.challenge_id == challenge.id,
            ChallengeCompletion.user_id == user.id,
        )
    )
    if completion is not None:
        return challenge_out(challenge, completion)
    reflection = payload.reflection.strip() if payload.reflection else None
    completion = ChallengeCompletion(
        challenge_id=challenge.id,
        user_id=user.id,
        reflection=reflection or None,
        xp_awarded=challenge.xp,
    )
    db.add(completion)
    locked_user.xp += challenge.xp
    locked_user.level = max(1, locked_user.xp // 250 + 1)
    await db.commit()
    await db.refresh(completion)
    return challenge_out(challenge, completion)


@router.get("/challenges/history", response_model=list[ChallengeResponse])
async def challenge_history(
    user: CurrentUser, db: DbSession, page: int = 1, limit: int = 10
) -> list[ChallengeResponse]:
    if user.is_guest or not user.is_approved:
        raise HTTPException(status_code=403, detail="Challenges are available to approved members")
    page = max(page, 1)
    limit = min(max(limit, 1), 50)
    rows = (
        await db.execute(
            select(Challenge, ChallengeCompletion)
            .join(ChallengeCompletion, ChallengeCompletion.challenge_id == Challenge.id)
            .where(ChallengeCompletion.user_id == user.id)
            .order_by(ChallengeCompletion.created_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        )
    ).all()
    return [challenge_out(challenge, completion) for challenge, completion in rows]


@router.post("/check-ins", response_model=CheckInResponse, status_code=status.HTTP_201_CREATED)
async def create_check_in(
    payload: CheckInRequest, user: CurrentUser, db: DbSession
) -> CheckInResponse:
    latest = await db.scalar(
        select(CheckIn)
        .where(CheckIn.user_id == user.id, CheckIn.completed.is_(True))
        .order_by(CheckIn.created_at.desc())
        .limit(1)
    )
    if latest and latest.created_at:
        created_at = latest.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=UTC)
        if datetime.now(UTC) - created_at < timedelta(hours=12):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Your next check-in will be available 12 hours after your last one.",
            )
    checkin = CheckIn(user_id=user.id, **payload.model_dump())
    db.add(checkin)
    await db.flush()
    checkin_dates = await db.scalars(
        select(CheckIn.created_at).where(CheckIn.user_id == user.id, CheckIn.completed.is_(True))
    )
    dates = [created_at.astimezone(UTC).date() for created_at in checkin_dates if created_at]
    user.streak = current_checkin_streak(dates, date.today())
    user.xp += 25
    user.level = max(1, user.xp // 250 + 1)
    await db.commit()
    await db.refresh(checkin)
    return CheckInResponse.model_validate(checkin)


@router.get("/check-ins", response_model=list[CheckInResponse])
async def list_check_ins(
    user: CurrentUser, db: DbSession, page: int = 1, limit: int = 20
) -> list[CheckInResponse]:
    page = max(page, 1)
    limit = min(max(limit, 1), 100)
    rows = (
        await db.scalars(
            select(CheckIn)
            .where(CheckIn.user_id == user.id)
            .order_by(CheckIn.created_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        )
    ).all()
    return [CheckInResponse.model_validate(row) for row in rows]


def quote_out(quote: Quote, saved_ids: set[int]) -> QuoteResponse:
    return QuoteResponse(
        id=quote.id,
        text=quote.text,
        author=quote.author,
        category=quote.category,
        is_featured=quote.is_featured,
        saved=quote.id in saved_ids,
        approval_status=quote.approval_status,
        submitted_by_user_id=quote.submitted_by_user_id,
    )


@router.get("/quotes", response_model=list[QuoteResponse])
async def list_quotes(
    user: CurrentUser,
    db: DbSession,
    category: str | None = None,
    saved_only: bool = False,
    page: int = 1,
    limit: int = 20,
) -> list[QuoteResponse]:
    page = max(page, 1)
    limit = min(max(limit, 1), 100)
    query = select(Quote).where(Quote.approval_status == "approved").order_by(Quote.is_featured.desc(), Quote.id)
    if category and category != "All":
        query = query.where(Quote.category == category)
    if saved_only:
        query = query.join(SavedQuote, SavedQuote.quote_id == Quote.id).where(
            SavedQuote.user_id == user.id
        )
    quotes = (await db.scalars(query.offset((page - 1) * limit).limit(limit))).all()
    saved_ids = set(
        (await db.scalars(select(SavedQuote.quote_id).where(SavedQuote.user_id == user.id))).all()
    )
    return [quote_out(quote, saved_ids) for quote in quotes]


@router.post("/quotes/{quote_id}/save", response_model=QuoteResponse)
async def save_quote(quote_id: int, user: CurrentUser, db: DbSession) -> QuoteResponse:
    quote = await db.get(Quote, quote_id)
    if quote is None or quote.approval_status != "approved":
        raise HTTPException(status_code=404, detail="Quote not found")
    saved = await db.scalar(
        select(SavedQuote).where(SavedQuote.user_id == user.id, SavedQuote.quote_id == quote_id)
    )
    if saved:
        await db.delete(saved)
        is_saved = False
    else:
        db.add(SavedQuote(user_id=user.id, quote_id=quote_id))
        is_saved = True
    await db.commit()
    return quote_out(quote, {quote_id} if is_saved else set())


@router.post("/quotes/submissions", response_model=QuoteResponse, status_code=status.HTTP_201_CREATED)
async def submit_quote(payload: QuoteSubmissionRequest, user: CurrentUser, db: DbSession) -> QuoteResponse:
    quote = Quote(
        text=payload.text.strip(),
        author=payload.author.strip(),
        category=payload.category,
        approval_status="pending",
        submitted_by_user_id=user.id,
    )
    db.add(quote)
    await db.commit()
    await db.refresh(quote)
    return quote_out(quote, set())


async def post_out(post: Post, user_id: int, db: AsyncSession) -> PostResponse:
    author = await db.get(User, post.user_id)
    reactions = (
        await db.scalars(select(PostReaction.kind).where(PostReaction.post_id == post.id))
    ).all()
    my_reaction = await db.scalar(
        select(PostReaction.kind).where(
            PostReaction.post_id == post.id, PostReaction.user_id == user_id
        )
    )
    liked_by = (
        await db.scalars(
            select(User.name)
            .join(PostReaction, PostReaction.user_id == User.id)
            .where(PostReaction.post_id == post.id, PostReaction.kind == "like")
            .order_by(User.name.asc())
        )
    ).all()
    comment_rows = (
        await db.scalars(
            select(Comment)
            .where(Comment.post_id == post.id)
            .order_by(Comment.created_at.asc())
            .limit(50)
        )
    ).all()
    comment_responses: list[CommentResponse] = []
    for comment in comment_rows:
        comment_author = await db.get(User, comment.user_id)
        comment_responses.append(
            CommentResponse(
                id=comment.id,
                post_id=comment.post_id,
                author=comment_author.name if comment_author else "Member",
                initials=(comment_author.name[0].upper() if comment_author else "M"),
                avatar_url=comment_author.avatar_url if comment_author else None,
                is_online=is_user_online(comment_author) if comment_author else False,
                text=comment.text,
                created_at=comment.created_at,
                mine=comment.user_id == user_id,
            )
        )
    counts = Counter(reactions)
    return PostResponse(
        id=post.id,
        author=author.name if author else "Member",
        initials=(author.name[0].upper() if author else "M"),
        avatar_url=author.avatar_url if author else None,
        is_online=is_user_online(author) if author else False,
        text=post.text,
        image_url=post.image_url,
        created_at=post.created_at,
        likes=counts["like"],
        dislikes=counts["dislike"],
        loves=counts["love"],
        my_reaction=my_reaction,
        comments=comment_responses,
        liked_by=list(liked_by),
        is_flagged=post.is_flagged,
        mine=post.user_id == user_id,
        post_type=post.post_type,
        shared_quote_id=post.quote_id,
    )


def normalise_upload(content: bytes, max_bytes: int) -> bytes:
    """Decode and resize an image so stored uploads stay within the output budget."""
    try:
        with Image.open(io.BytesIO(content)) as source:
            if source.width * source.height > 36_000_000:
                raise HTTPException(
                    status_code=413,
                    detail="This image has too many pixels to process safely.",
                )
            source.load()
            prepared = ImageOps.exif_transpose(source)
            if prepared.mode not in {"RGB", "RGBA"}:
                prepared = prepared.convert("RGBA" if "transparency" in prepared.info else "RGB")
            prepared.thumbnail((2400, 2400), Image.Resampling.LANCZOS)
    except (Image.DecompressionBombError, UnidentifiedImageError, OSError, ValueError) as exc:
        raise HTTPException(
            status_code=415, detail="The uploaded file is not a valid image"
        ) from exc

    quality = 88
    scale = 1.0
    while quality >= 42:
        candidate = prepared.copy()
        if scale < 1:
            candidate.thumbnail(
                (max(320, int(prepared.width * scale)), max(320, int(prepared.height * scale))),
                Image.Resampling.LANCZOS,
            )
        output = io.BytesIO()
        candidate.save(output, format="WEBP", quality=quality, method=6)
        encoded = output.getvalue()
        if len(encoded) <= max_bytes:
            return encoded
        if quality > 42:
            quality -= 8
        else:
            scale *= 0.8
            quality = 82

    raise HTTPException(
        status_code=413,
        detail="This image could not be resized below the upload limit.",
    )


async def save_post_image(image: UploadFile) -> str:
    settings = get_settings()
    allowed_types = {
        "image/jpeg": ("jpg", b"\xff\xd8\xff"),
        "image/png": ("png", b"\x89PNG\r\n\x1a\n"),
        "image/webp": ("webp", b"RIFF"),
    }
    image_format = allowed_types.get(image.content_type or "")
    if image_format is None:
        raise HTTPException(status_code=415, detail="Only JPEG, PNG, and WebP images are supported")
    source_limit = getattr(
        settings, "max_source_upload_bytes", settings.max_upload_bytes * 4
    )
    content = await image.read(source_limit + 1)
    if len(content) > source_limit:
        raise HTTPException(
            status_code=413,
            detail="This image is too large to process. Please choose an image under 40 MB.",
        )
    signature = image_format[1]
    if not content.startswith(signature) or (
        image_format[0] == "webp" and content[8:12] != b"WEBP"
    ):
        raise HTTPException(status_code=415, detail="The uploaded file is not a valid image")
    content = normalise_upload(content, settings.max_upload_bytes)
    if settings.use_cloudinary:
        if not all(
            (
                settings.cloudinary_cloud_name,
                settings.cloudinary_api_key,
                settings.cloudinary_api_secret,
            )
        ):
            raise HTTPException(status_code=503, detail="Image storage is not configured")
        try:
            cloudinary.config(
                cloud_name=settings.cloudinary_cloud_name,
                api_key=settings.cloudinary_api_key,
                api_secret=settings.cloudinary_api_secret,
                secure=True,
            )
            result = await asyncio.to_thread(
                cloudinary.uploader.upload,
                io.BytesIO(content),
                folder="safe-space-saturdays",
                resource_type="image",
                format="webp",
            )
        except Exception as exc:
            raise HTTPException(
                status_code=502, detail="Image storage is temporarily unavailable"
            ) from exc
        secure_url = result.get("secure_url")
        if not isinstance(secure_url, str) or not secure_url.startswith("https://"):
            raise HTTPException(status_code=502, detail="Image storage returned an invalid URL")
        return secure_url
    filename = f"{uuid4().hex}.webp"
    destination: Path = settings.upload_dir / filename
    await asyncio.to_thread(destination.write_bytes, content)
    return f"/uploads/{filename}"


@router.get("/community/posts", response_model=list[PostResponse])
async def list_posts(
    user: CurrentUser,
    db: DbSession,
    page: int = 1,
    limit: int = 20,
    sort: str = "latest",
) -> list[PostResponse]:
    page = max(page, 1)
    limit = min(max(limit, 1), 100)
    if sort not in {"latest", "earliest", "most_liked", "most_replied"}:
        raise HTTPException(status_code=422, detail="Invalid community sort")
    query = select(Post).where(Post.is_hidden.is_(False))
    if sort == "earliest":
        query = query.order_by(Post.created_at.asc())
    elif sort == "most_liked":
        query = (
            query.outerjoin(
                PostReaction,
                and_(PostReaction.post_id == Post.id, PostReaction.kind == "like"),
            )
            .group_by(Post.id)
            .order_by(func.count(PostReaction.id).desc(), Post.created_at.desc())
        )
    elif sort == "most_replied":
        query = (
            query.outerjoin(Comment, Comment.post_id == Post.id)
            .group_by(Post.id)
            .order_by(func.count(Comment.id).desc(), Post.created_at.desc())
        )
    else:
        query = query.order_by(Post.created_at.desc())
    rows = (await db.scalars(query.offset((page - 1) * limit).limit(limit))).all()
    return [await post_out(post, user.id, db) for post in rows]


@router.get("/community/announcements", response_model=list[AnnouncementResponse])
async def list_announcements(user: CurrentUser, db: DbSession) -> list[AnnouncementResponse]:
    del user
    announcements = (
        await db.scalars(
            select(Announcement)
            .where(Announcement.is_published.is_(True))
            .order_by(Announcement.created_at.desc())
            .limit(20)
        )
    ).all()
    return [AnnouncementResponse.model_validate(item) for item in announcements]


async def list_activity_posts(
    user: CurrentUser,
    db: DbSession,
    reaction_kinds: tuple[str, ...] | None = None,
    replied_only: bool = False,
    page: int = 1,
    limit: int = 20,
) -> list[PostResponse]:
    page = max(page, 1)
    limit = min(max(limit, 1), 100)
    query = select(Post).where(Post.is_hidden.is_(False))
    if reaction_kinds:
        query = query.join(PostReaction, PostReaction.post_id == Post.id).where(
            PostReaction.user_id == user.id, PostReaction.kind.in_(reaction_kinds)
        )
    if replied_only:
        query = query.join(Comment, Comment.post_id == Post.id).where(Comment.user_id == user.id)
    rows = (
        await db.scalars(
            query.order_by(Post.created_at.desc())
            .distinct()
            .offset((page - 1) * limit)
            .limit(limit)
        )
    ).all()
    return [await post_out(post, user.id, db) for post in rows]


@router.get("/community/activity/liked", response_model=list[PostResponse])
async def liked_posts(
    user: CurrentUser, db: DbSession, page: int = 1, limit: int = 10
) -> list[PostResponse]:
    return await list_activity_posts(
        user, db, reaction_kinds=("like", "love"), page=page, limit=limit
    )


@router.get("/community/activity/replied", response_model=list[PostResponse])
async def replied_posts(
    user: CurrentUser, db: DbSession, page: int = 1, limit: int = 10
) -> list[PostResponse]:
    return await list_activity_posts(user, db, replied_only=True, page=page, limit=limit)


@router.post("/community/posts", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
async def create_post(payload: PostCreateRequest, user: CurrentUser, db: DbSession) -> PostResponse:
    ensure_can_post(user)
    post = Post(user_id=user.id, text=payload.text.strip())
    db.add(post)
    await db.commit()
    await db.refresh(post)
    await grant_community_post_reward(db, user.id, post.id)
    await db.commit()
    return await post_out(post, user.id, db)


@router.patch("/community/posts/{post_id}", response_model=PostResponse)
async def edit_community_post(
    post_id: int,
    payload: PostUpdateRequest,
    user: CurrentUser,
    db: DbSession,
) -> PostResponse:
    post = await db.get(Post, post_id)
    if post is None or post.is_hidden:
        raise HTTPException(status_code=404, detail="Post not found")
    if post.user_id != user.id:
        raise HTTPException(status_code=403, detail="You can only edit your own posts")
    post.text = payload.text.strip()
    await db.commit()
    await db.refresh(post)
    return await post_out(post, user.id, db)


@router.post("/community/posts/from-quote/{quote_id}", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
async def share_quote_to_community(quote_id: int, user: CurrentUser, db: DbSession) -> PostResponse:
    ensure_can_post(user)
    quote = await db.get(Quote, quote_id)
    if quote is None or quote.approval_status != "approved":
        raise HTTPException(status_code=404, detail="Quote not found")
    post = Post(
        user_id=user.id,
        text=f'“{quote.text}” — {quote.author}',
        post_type="shared_quote",
        quote_id=quote.id,
    )
    db.add(post)
    await db.commit()
    await db.refresh(post)
    await grant_community_post_reward(db, user.id, post.id)
    await db.commit()
    return await post_out(post, user.id, db)


@router.post(
    "/community/posts/with-image",
    response_model=PostResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_post_with_image(
    text: Annotated[str, Form(min_length=1, max_length=2000)],
    user: CurrentUser,
    db: DbSession,
    image: Annotated[UploadFile, File(...)],
) -> PostResponse:
    ensure_can_post(user)
    image_url = await save_post_image(image)
    post = Post(user_id=user.id, text=text.strip(), image_url=image_url)
    db.add(post)
    await db.commit()
    await db.refresh(post)
    await grant_community_post_reward(db, user.id, post.id)
    await db.commit()
    return await post_out(post, user.id, db)


@router.post("/community/posts/{post_id}/reactions", response_model=PostResponse)
async def react_to_post(
    post_id: int, payload: ReactionRequest, user: CurrentUser, db: DbSession
) -> PostResponse:
    post = await db.get(Post, post_id)
    if post is None or post.is_hidden:
        raise HTTPException(status_code=404, detail="Post not found")
    reaction = await db.scalar(
        select(PostReaction).where(PostReaction.post_id == post_id, PostReaction.user_id == user.id)
    )
    if reaction:
        if reaction.kind == payload.kind:
            await db.delete(reaction)
        else:
            reaction.kind = payload.kind
    else:
        db.add(PostReaction(post_id=post_id, user_id=user.id, kind=payload.kind))
    await db.commit()
    return await post_out(post, user.id, db)


@router.post(
    "/community/posts/{post_id}/comments",
    response_model=CommentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def comment_on_post(
    post_id: int, payload: CommentCreateRequest, user: CurrentUser, db: DbSession
) -> CommentResponse:
    ensure_can_post(user)
    if await db.get(Post, post_id) is None:
        raise HTTPException(status_code=404, detail="Post not found")
    comment = Comment(post_id=post_id, user_id=user.id, text=payload.text.strip())
    db.add(comment)
    await db.commit()
    await db.refresh(comment)
    return CommentResponse(
        id=comment.id,
        post_id=comment.post_id,
        author=user.name,
        initials=user.name[0].upper(),
        is_online=True,
        text=comment.text,
        created_at=comment.created_at,
        mine=True,
    )


@router.patch("/community/comments/{comment_id}", response_model=CommentResponse)
async def edit_comment(
    comment_id: int,
    payload: CommentUpdateRequest,
    user: CurrentUser,
    db: DbSession,
) -> CommentResponse:
    comment = await db.get(Comment, comment_id)
    if comment is None:
        raise HTTPException(status_code=404, detail="Comment not found")
    if comment.user_id != user.id:
        raise HTTPException(status_code=403, detail="You can only edit your own replies")
    comment.text = payload.text.strip()
    await db.commit()
    await db.refresh(comment)
    return CommentResponse(
        id=comment.id,
        post_id=comment.post_id,
        author=user.name,
        initials=user.name[0].upper(),
        avatar_url=user.avatar_url,
        is_online=True,
        text=comment.text,
        created_at=comment.created_at,
        mine=True,
    )


@router.post("/community/posts/{post_id}/moderation", response_model=PostResponse)
async def moderate_post(
    post_id: int,
    payload: CommunityModerationRequest,
    moderator: CurrentAdmin,
    db: DbSession,
) -> PostResponse:
    if not can_moderate_community(moderator):
        raise HTTPException(status_code=403, detail="Community moderation access required")
    post = await db.get(Post, post_id)
    if post is None or post.is_hidden:
        raise HTTPException(status_code=404, detail="Post not found")
    if payload.action == "flag":
        post.is_flagged = True
    elif payload.action == "unflag":
        post.is_flagged = False
    else:
        author = await db.get(User, post.user_id)
        if author is None:
            raise HTTPException(status_code=404, detail="Post author not found")
        author.posting_timeout_until = datetime.now(UTC) + timedelta(hours=2)
    await db.commit()
    await db.refresh(post)
    return await post_out(post, moderator.id, db)


@router.delete("/community/posts/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_community_post(
    post_id: int, moderator: CurrentAdmin, db: DbSession
) -> None:
    if not can_moderate_community(moderator):
        raise HTTPException(status_code=403, detail="Community moderation access required")
    post = await db.get(Post, post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")
    post.is_hidden = True
    await db.commit()


@router.get("/games", response_model=list[GameResponse])
async def list_games(
    user: CurrentUser, db: DbSession, page: int = 1, limit: int = 20
) -> list[GameResponse]:
    page = max(page, 1)
    limit = min(max(limit, 1), 100)
    games = [
        GameResponse.model_validate(game)
        for game in (
            await db.scalars(
            select(Game)
            .where(Game.name != "Bingo")
            .where((Game.name != "CSEC IT Mock Exam") | can_access_csec_exam(user))
            .order_by(Game.is_featured.desc(), Game.id)
                .offset((page - 1) * limit)
                .limit(limit)
            )
        ).all()
    ]
    return games


async def room_out(
    room: GameRoom, user_id: int, db: AsyncSession, spectator: bool = False
) -> RoomResponse:
    game = await db.get(Game, room.game_id)
    participants = (
        await db.scalar(
            select(func.count(RoomParticipant.id)).where(RoomParticipant.room_id == room.id)
        )
        or 0
    )
    participant = await db.scalar(
        select(RoomParticipant).where(
            RoomParticipant.room_id == room.id, RoomParticipant.user_id == user_id
        )
    )
    active_match = await db.scalar(
        select(GameMatch.id)
        .where(GameMatch.room_id == room.id, GameMatch.status == "active")
        .limit(1)
    )
    return RoomResponse(
        id=room.id,
        name=room.name,
        game=game.name if game else "Game",
        players=participants,
        max_players=room.max_players,
        status=room.status,
        joined=participant is not None,
        is_host=room.host_id == user_id,
        match_id=active_match,
        ready=room_participant_is_ready(room, participant) if participant else False,
        bot_difficulty=room.bot_difficulty,
        fill_with_bots=room.fill_with_bots,
        invite_token=room.invite_token if participant is not None or spectator else None,
        room_code=room.room_code if participant is not None or spectator else None,
        abc_categories=room.abc_categories,
        abc_majority_invalid=room.abc_majority_invalid,
    )


@router.get("/games/rooms", response_model=list[RoomResponse])
async def list_rooms(
    user: CurrentUser, db: DbSession, page: int = 1, limit: int = 10
) -> list[RoomResponse]:
    page = max(page, 1)
    limit = min(max(limit, 1), 100)
    rooms = (
        await db.scalars(
            select(GameRoom)
            .where(GameRoom.status.in_(["open", "active"]))
            .order_by(GameRoom.created_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        )
    ).all()
    visible_rooms: list[RoomResponse] = []
    for room in rooms:
        game = await db.get(Game, room.game_id)
        if game is not None and game.name == "CSEC IT Mock Exam" and not can_access_csec_exam(user):
            continue
        visible_rooms.append(await room_out(room, user.id, db))
    return visible_rooms


@router.post("/games/rooms", response_model=RoomResponse, status_code=status.HTTP_201_CREATED)
async def create_room(payload: RoomCreateRequest, user: CurrentUser, db: DbSession) -> RoomResponse:
    game = await db.get(Game, payload.game_id)
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")
    if game.name == "CSEC IT Mock Exam" and not can_access_csec_exam(user):
        raise HTTPException(status_code=403, detail="This private exam is not available to your account")
    capacity = game_capacity(game.name)
    if capacity and payload.max_players > capacity:
        raise HTTPException(
            status_code=422,
            detail=f"{game.name} supports at most {game_capacity(game.name)} players",
        )
    room_code = None
    if game.name.casefold() in {"together", "linked together"}:
        for _ in range(8):
            candidate = f"{secrets.choice(('PURPLE', 'HAPPY', 'SPACE', 'SUNNY', 'CLOUD', 'MANGO'))}{secrets.randbelow(90) + 10}"
            if await db.scalar(select(GameRoom.id).where(GameRoom.room_code == candidate)) is None:
                room_code = candidate
                break
        if room_code is None:
            raise HTTPException(status_code=503, detail="Could not create a room code")
        payload = payload.model_copy(update={"fill_with_bots": False, "max_players": min(payload.max_players, 5)})
    room = GameRoom(
        game_id=payload.game_id,
        host_id=user.id,
        name=payload.name.strip(),
        max_players=payload.max_players,
        fill_with_bots=payload.fill_with_bots,
        bot_difficulty=payload.bot_difficulty,
        abc_categories=None,
        abc_majority_invalid=True,
        invite_token=secrets.token_urlsafe(32),
        room_code=room_code,
    )
    db.add(room)
    await db.flush()
    db.add(RoomParticipant(room_id=room.id, user_id=user.id, seat_index=0, ready=True))
    await db.commit()
    return await room_out(room, user.id, db)


@router.patch("/games/rooms/{room_id}/abc-settings", response_model=RoomResponse)
async def update_abc_room_settings(
    room_id: int, payload: AbcRoomSettingsRequest, user: CurrentUser, db: DbSession
) -> RoomResponse:
    room = await db.scalar(select(GameRoom).where(GameRoom.id == room_id).with_for_update())
    if room is None:
        raise HTTPException(status_code=404, detail="Room not found")
    if room.host_id != user.id:
        raise HTTPException(status_code=403, detail="Only the room host can change ABC settings")
    if room.status != "open":
        raise HTTPException(status_code=409, detail="ABC settings can only change before the game starts")
    game = await db.get(Game, room.game_id)
    if game is None or game_type_for_name(game.name) != "abc-fast-slow":
        raise HTTPException(status_code=409, detail="This room is not an ABC Fast or Slow room")
    categories = list(dict.fromkeys(category.strip()[:40] for category in payload.categories if category.strip()))
    if not categories:
        raise HTTPException(status_code=422, detail="Add at least one category")
    participant_count = await db.scalar(select(func.count(RoomParticipant.id)).where(RoomParticipant.room_id == room.id)) or 0
    if payload.max_players < participant_count:
        raise HTTPException(status_code=409, detail="Capacity cannot be below the number of players already in the room")
    room.max_players = payload.max_players
    room.abc_categories = categories
    room.abc_majority_invalid = payload.majority_invalid
    await db.commit()
    return await room_out(room, user.id, db)


@router.get("/games/rooms/invite/{invite_token}", response_model=RoomInviteResponse)
async def get_room_invite(invite_token: str, db: DbSession) -> RoomInviteResponse:
    room = await db.scalar(select(GameRoom).where(GameRoom.invite_token == invite_token))
    if room is None or room.status not in {"open", "active"}:
        raise HTTPException(status_code=404, detail="This room invite is no longer available")
    game = await db.get(Game, room.game_id)
    players = await db.scalar(
        select(func.count(RoomParticipant.id)).where(RoomParticipant.room_id == room.id)
    ) or 0
    match_id = await db.scalar(
        select(GameMatch.id)
        .where(GameMatch.room_id == room.id, GameMatch.status == "active")
        .limit(1)
    )
    return RoomInviteResponse(
        id=room.id,
        name=room.name,
        game=game.name if game else "Game",
        players=players,
        max_players=room.max_players,
        status=room.status,
        match_id=match_id,
        invite_token=room.invite_token,
        room_code=room.room_code,
    )


@router.post("/games/rooms/invite/{invite_token}/join", response_model=RoomResponse)
async def join_room_invite(invite_token: str, user: CurrentUser, db: DbSession) -> RoomResponse:
    room = await db.scalar(select(GameRoom).where(GameRoom.invite_token == invite_token).with_for_update())
    if room is None or room.status != "open":
        raise HTTPException(status_code=404, detail="Room is not accepting players")
    count = await db.scalar(select(func.count(RoomParticipant.id)).where(RoomParticipant.room_id == room.id)) or 0
    existing = await db.scalar(select(RoomParticipant.id).where(RoomParticipant.room_id == room.id, RoomParticipant.user_id == user.id))
    if existing is None:
        if count >= room.max_players:
            raise HTTPException(status_code=409, detail="Room is full")
        db.add(RoomParticipant(room_id=room.id, user_id=user.id, seat_index=count))
        await db.commit()
    return await room_out(room, user.id, db)


@router.post("/games/rooms/invite/{invite_token}/guest", response_model=GuestRoomJoinResponse)
async def join_room_as_guest(
    invite_token: str,
    payload: GuestRoomJoinRequest,
    response: Response,
    db: DbSession,
) -> RoomResponse:
    room = await db.scalar(select(GameRoom).where(GameRoom.invite_token == invite_token).with_for_update())
    if room is None or room.status != "open":
        raise HTTPException(status_code=404, detail="Room is not accepting players")
    guest_name = payload.name.strip()
    existing_guest = await db.scalar(
        select(User)
        .join(RoomParticipant, RoomParticipant.user_id == User.id)
        .where(
            RoomParticipant.room_id == room.id,
            User.is_guest.is_(True),
            func.lower(User.name) == guest_name.casefold(),
        )
    )
    if existing_guest is not None:
        if existing_guest.email.endswith("@guest.invalid"):
            existing_guest.email = new_guest_email()
        guest_user = user_response(existing_guest)
        guest_room = await room_out(room, existing_guest.id, db)
        await set_session(response, db, existing_guest, remember_me=False)
        return GuestRoomJoinResponse(room=guest_room, user=guest_user)
    count = await db.scalar(select(func.count(RoomParticipant.id)).where(RoomParticipant.room_id == room.id)) or 0
    if count >= room.max_players:
        raise HTTPException(status_code=409, detail="Room is full")
    guest = User(
        name=guest_name,
        email=new_guest_email(),
        password_hash=hash_password(secrets.token_urlsafe(32)),
        role="guest",
        is_guest=True,
        is_approved=True,
    )
    db.add(guest)
    await db.flush()
    db.add(RoomParticipant(room_id=room.id, user_id=guest.id, seat_index=count, ready=True))
    await db.flush()
    guest_user = user_response(guest)
    guest_room = await room_out(room, guest.id, db)
    await set_session(response, db, guest, remember_me=False)
    return GuestRoomJoinResponse(room=guest_room, user=guest_user)


@router.post("/games/rooms/invite/{invite_token}/spectate", response_model=GuestRoomJoinResponse)
async def spectate_room_as_guest(
    invite_token: str,
    payload: GuestRoomJoinRequest,
    response: Response,
    db: DbSession,
) -> GuestRoomJoinResponse:
    room = await db.scalar(select(GameRoom).where(GameRoom.invite_token == invite_token))
    if room is None or room.status != "active":
        raise HTTPException(status_code=404, detail="This game is not currently in progress")
    guest_name = payload.name.strip()
    existing_guest = await db.scalar(
        select(User).where(User.is_guest.is_(True), func.lower(User.name) == guest_name.casefold())
    )
    guest = existing_guest
    if guest is None:
        guest = User(
            name=guest_name,
            email=new_guest_email(),
            password_hash=hash_password(secrets.token_urlsafe(32)),
            role="guest",
            is_guest=True,
            is_approved=True,
        )
        db.add(guest)
        await db.flush()
    guest_room = await room_out(room, guest.id, db, spectator=True)
    await set_session(response, db, guest, remember_me=False)
    return GuestRoomJoinResponse(room=guest_room, user=user_response(guest))


@router.post("/games/rooms/{room_id}/join", response_model=RoomResponse)
async def join_room(room_id: int, user: CurrentUser, db: DbSession) -> RoomResponse:
    room = await db.scalar(select(GameRoom).where(GameRoom.id == room_id).with_for_update())
    if room is None or room.status != "open":
        raise HTTPException(status_code=404, detail="Room not available")
    game = await db.get(Game, room.game_id)
    if game is not None and game.name == "CSEC IT Mock Exam" and not can_access_csec_exam(user):
        raise HTTPException(status_code=403, detail="This private exam is not available to your account")
    count = (
        await db.scalar(
            select(func.count(RoomParticipant.id)).where(RoomParticipant.room_id == room_id)
        )
        or 0
    )
    if count >= room.max_players:
        raise HTTPException(status_code=409, detail="Room is full")
    if (
        await db.scalar(
            select(RoomParticipant.id).where(
                RoomParticipant.room_id == room_id, RoomParticipant.user_id == user.id
            )
        )
        is None
    ):
        if count >= room.max_players:
            raise HTTPException(status_code=409, detail="Room is full")
        db.add(RoomParticipant(room_id=room_id, user_id=user.id, seat_index=count))
        await db.commit()
    return await room_out(room, user.id, db)


@router.get("/games/rooms/{room_id}", response_model=RoomResponse)
async def get_room(
    room_id: int, user: CurrentUser, db: DbSession, spectate: bool = False
) -> RoomResponse:
    room = await db.get(GameRoom, room_id)
    if room is None or room.status not in {"open", "active"}:
        raise HTTPException(status_code=404, detail="Room not available")
    game = await db.get(Game, room.game_id)
    if game is not None and game.name == "CSEC IT Mock Exam" and not can_access_csec_exam(user):
        raise HTTPException(status_code=403, detail="This private exam is not available to your account")
    participant = await db.scalar(
        select(RoomParticipant.id).where(
            RoomParticipant.room_id == room_id, RoomParticipant.user_id == user.id
        )
    )
    if participant is None and not (spectate and room.status == "active"):
        raise HTTPException(status_code=403, detail="You are not a participant in this room")
    return await room_out(room, user.id, db, spectator=participant is None)


@router.get("/games/rooms/{room_id}/participants", response_model=list[RoomParticipantResponse])
async def list_room_participants(
    room_id: int, user: CurrentUser, db: DbSession, spectate: bool = False
) -> list[RoomParticipantResponse]:
    room = await db.get(GameRoom, room_id)
    if room is None:
        raise HTTPException(status_code=404, detail="Room not found")
    membership = await db.scalar(
        select(RoomParticipant.id).where(
            RoomParticipant.room_id == room_id, RoomParticipant.user_id == user.id
        )
    )
    if membership is None and not (spectate and room.status == "active"):
        raise HTTPException(status_code=403, detail="You are not a participant in this room")
    participants = (
        await db.execute(
            select(RoomParticipant, User)
            .join(User, User.id == RoomParticipant.user_id)
            .where(RoomParticipant.room_id == room_id)
            .order_by(RoomParticipant.seat_index, RoomParticipant.joined_at)
        )
    ).all()
    return [
        RoomParticipantResponse(
            user_id=participant.user_id,
            name=member.name,
            avatar_url=member.avatar_url,
            seat_index=participant.seat_index,
            ready=room_participant_is_ready(room, participant),
            is_host=room.host_id == participant.user_id,
        )
        for participant, member in participants
    ]


@router.delete("/games/rooms/{room_id}/participants/{participant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def kick_room_participant(
    room_id: int, participant_id: int, user: CurrentUser, db: DbSession
) -> Response:
    """Let the host remove a guest from an open lobby before the match starts."""
    room = await db.scalar(select(GameRoom).where(GameRoom.id == room_id).with_for_update())
    if room is None:
        raise HTTPException(status_code=404, detail="Room not found")
    if room.host_id != user.id:
        raise HTTPException(status_code=403, detail="Only the host can remove players")
    if room.status != "open":
        raise HTTPException(status_code=409, detail="Players can only be removed before the game starts")
    participant = await db.scalar(
        select(RoomParticipant).where(
            RoomParticipant.room_id == room_id,
            RoomParticipant.user_id == participant_id,
        ).with_for_update()
    )
    if participant is None:
        raise HTTPException(status_code=404, detail="Player is not in this room")
    if participant.user_id == room.host_id:
        raise HTTPException(status_code=400, detail="The host cannot remove themselves")
    await db.delete(participant)
    remaining = (
        await db.scalars(
            select(RoomParticipant)
            .where(RoomParticipant.room_id == room_id)
            .order_by(RoomParticipant.joined_at, RoomParticipant.id)
        )
    ).all()
    for seat_index, member in enumerate(remaining):
        member.seat_index = seat_index
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/games/rooms/{room_id}", status_code=status.HTTP_204_NO_CONTENT)
async def end_game_room(room_id: int, user: CurrentUser, db: DbSession) -> Response:
    room = await db.get(GameRoom, room_id, with_for_update=True)
    if room is None:
        raise HTTPException(status_code=404, detail="Room not found")
    if room.host_id != user.id:
        raise HTTPException(status_code=403, detail="Only the room host can end this game")
    guest_user_ids = (
        await db.scalars(
            select(User.id)
            .join(RoomParticipant, RoomParticipant.user_id == User.id)
            .where(RoomParticipant.room_id == room_id, User.is_guest.is_(True))
        )
    ).all()
    match_id = await db.scalar(
        select(GameMatch.id).where(GameMatch.room_id == room_id).limit(1)
    )
    if match_id is not None:
        live_match = match_manager.get(match_id) or universal_matches.get(match_id)
        if live_match is not None:
            for socket in list(live_match.sockets):
                try:
                    await socket.send_json(
                        {"type": "session_ended", "detail": "The host ended this game session."}
                    )
                except Exception:
                    live_match.sockets.pop(socket, None)
        await realtime_bus.publish(
            match_channel(match_id),
            {
                "origin": get_settings().realtime_node_id,
                "payload": {
                    "type": "session_ended",
                    "detail": "The host ended this game session.",
                },
            },
        )
        match_manager.matches.pop(match_id, None)
        universal_matches.matches.pop(match_id, None)
        if match_manager.room_matches.get(room_id) == match_id:
            match_manager.room_matches.pop(room_id, None)
    await db.delete(room)
    await db.flush()
    for guest_user_id in guest_user_ids:
        still_participating = await db.scalar(
            select(RoomParticipant.id).where(RoomParticipant.user_id == guest_user_id).limit(1)
        )
        if still_participating is None:
            await db.execute(delete(Session).where(Session.user_id == guest_user_id))
            guest = await db.get(User, guest_user_id)
            if guest is not None:
                await db.delete(guest)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/games/rooms/cleanup-bot-rooms", response_model=RoomCleanupResponse)
async def cleanup_bot_rooms(admin: CurrentAdmin, db: DbSession) -> RoomCleanupResponse:
    """Remove active rooms that only contain their host plus generated bot seats."""
    rooms = (
        await db.scalars(select(GameRoom).where(GameRoom.status == "active").with_for_update())
    ).all()
    deleted = 0
    for room in rooms:
        participant_count = await db.scalar(
            select(func.count(RoomParticipant.id)).where(RoomParticipant.room_id == room.id)
        ) or 0
        active_match = await db.scalar(
            select(GameMatch).where(GameMatch.room_id == room.id, GameMatch.status == "active").limit(1)
        )
        if participant_count != 1 or active_match is None:
            continue
        bot_count = await db.scalar(
            select(func.count(GameMatchPlayer.id)).where(
                GameMatchPlayer.match_id == active_match.id,
                GameMatchPlayer.player_type == "bot",
            )
        ) or 0
        if bot_count == 0:
            continue
        live_match = match_manager.get(active_match.id) or universal_matches.get(active_match.id)
        if live_match is not None:
            for socket in list(live_match.sockets):
                try:
                    await socket.send_json({"type": "session_ended", "detail": "This stale bot room was cleaned up."})
                except Exception:
                    live_match.sockets.pop(socket, None)
            match_manager.matches.pop(active_match.id, None)
            universal_matches.matches.pop(active_match.id, None)
            if match_manager.room_matches.get(room.id) == active_match.id:
                match_manager.room_matches.pop(room.id, None)
        await db.delete(room)
        deleted += 1
    await db.commit()
    return RoomCleanupResponse(deleted=deleted)


@router.post("/games/rooms/{room_id}/ready", response_model=RoomResponse)
async def set_room_ready(room_id: int, user: CurrentUser, db: DbSession) -> RoomResponse:
    room = await db.get(GameRoom, room_id)
    participant = await db.scalar(
        select(RoomParticipant).where(
            RoomParticipant.room_id == room_id, RoomParticipant.user_id == user.id
        )
    )
    if room is None or participant is None or room.status != "open":
        raise HTTPException(status_code=409, detail="Room is not accepting readiness changes")
    participant.ready = True if participant.user_id == room.host_id else not participant.ready
    await db.commit()
    return await room_out(room, user.id, db)


@router.post("/games/rooms/{room_id}/game", response_model=RoomResponse)
async def change_room_game(
    room_id: int,
    payload: RoomGameChangeRequest,
    user: CurrentUser,
    db: DbSession,
) -> RoomResponse:
    room = await db.scalar(select(GameRoom).where(GameRoom.id == room_id).with_for_update())
    if room is None:
        raise HTTPException(status_code=404, detail="Room not found")
    if room.host_id != user.id:
        raise HTTPException(status_code=403, detail="Only the room host can change the game")
    if room.status not in {"open", "active"}:
        raise HTTPException(status_code=409, detail="This room is no longer available")
    game = await db.get(Game, payload.game_id)
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")
    capacity = game_capacity(game.name)
    participants = (
        await db.scalars(select(RoomParticipant).where(RoomParticipant.room_id == room.id))
    ).all()
    if capacity and (room.max_players > capacity or len(participants) > capacity):
        raise HTTPException(
            status_code=409,
            detail=f"{game.name} supports at most {capacity} players; remove players or choose another game",
        )
    if room.game_id != game.id:
        active_id = await db.scalar(
            select(GameMatch.id).where(GameMatch.room_id == room.id, GameMatch.status == "active").limit(1)
        )
        if active_id is not None:
            live_match = match_manager.get(active_id) or universal_matches.get(active_id)
            if live_match is not None:
                event = {"type": "game_changed", "room_id": room.id, "game": game.name}
                for socket in list(live_match.sockets):
                    try:
                        await socket.send_json(event)
                    except Exception:
                        live_match.sockets.pop(socket, None)
                await realtime_bus.publish(
                    match_channel(active_id),
                    {"origin": get_settings().realtime_node_id, "payload": event},
                )
            match_manager.matches.pop(active_id, None)
            universal_matches.matches.pop(active_id, None)
            if match_manager.room_matches.get(room.id) == active_id:
                match_manager.room_matches.pop(room.id, None)
            old_match = await db.get(GameMatch, active_id)
            if old_match is not None:
                await db.delete(old_match)
        room.game_id = game.id
        room.status = "open"
        for participant in participants:
            participant.ready = participant.user_id == room.host_id
    await db.commit()
    return await room_out(room, user.id, db)


@router.post("/games/matches", response_model=MatchResponse, status_code=status.HTTP_201_CREATED)
async def create_match(
    payload: MatchCreateRequest, user: CurrentUser, db: DbSession
) -> MatchResponse:
    room = await db.scalar(select(GameRoom).where(GameRoom.id == payload.room_id).with_for_update())
    if room is None or room.status != "open":
        raise HTTPException(status_code=404, detail="Room not available")
    if room.host_id != user.id:
        raise HTTPException(status_code=403, detail="Only the room host can start a match")
    joined = await db.scalar(
        select(RoomParticipant.id).where(
            RoomParticipant.room_id == room.id, RoomParticipant.user_id == user.id
        )
    )
    if joined is None:
        raise HTTPException(status_code=403, detail="Join the room before starting a match")
    game = await db.get(Game, room.game_id)
    if game is None or game.name != "Connect Four":
        raise HTTPException(status_code=409, detail="This game is not playable yet")
    existing_id = match_manager.room_matches.get(room.id)
    existing_match = match_manager.get(existing_id) if existing_id else None
    if existing_match:
        return match_response(existing_match, user.id)
    seats, player_ids, bot_players, player_names = await build_match_seats(
        room, "connect-four", user.id, db, payload.with_bot
    )
    progress = await db.scalar(select(GameProgress).where(
        GameProgress.user_id == user.id, GameProgress.game_type == "connect-four"
    ))
    game_level = progress.level if progress else 1
    game_streak = progress.current_streak if progress else 0
    difficulty = "thoughtful" if game_level >= 2 else payload.bot_difficulty
    match = match_manager.create(
        room.id, user.id, payload.with_bot, difficulty, game_level, game_streak, player_ids, player_names
    )
    room.status = "active"
    await create_persisted_match(
        db, match.id, room.id, "connect-four", user.id, match.snapshot(), seats
    )
    await db.commit()
    return match_response(match, user.id)


@router.get("/games/matches/{match_id}", response_model=MatchResponse)
async def get_match(match_id: str, user: CurrentUser, spectate: bool = False) -> MatchResponse:
    match = match_manager.get(match_id)
    if match is None:
        match, _ = await hydrate_match(match_id)
    if match is None:
        raise HTTPException(status_code=404, detail="Match not found")
    is_spectator = user.id not in match.player_ids
    if is_spectator and not spectate:
        raise HTTPException(status_code=403, detail="You are not a player in this match")
    return match_response(match, None if is_spectator else user.id, spectator=is_spectator)


async def apply_connect_action(
    match: LiveMatch,
    user_id: int,
    action: dict[str, Any],
    db: AsyncSession,
) -> None:
    """Apply and persist one Connect Four action before broadcasting it."""
    async with match.lock:
        previous_state = match.state
        previous_version = match.version
        previous_starting_player = match.starting_player
        previous_reward_granted = match.reward_granted
        persisted = await db.scalar(
            select(GameMatch).where(GameMatch.id == match.id).with_for_update()
        )
        if persisted is None:
            raise ValueError("Persisted match not found")
        if persisted.version > match.version:
            apply_connect_snapshot(match, persisted.state)
            match.version = persisted.version
        try:
            if action.get("action") == "play_again":
                await settle_completed_match_progress(db, match, user_id)
                await match_manager.play_again_locked(match, user_id, broadcast=True, run_bot=False)
            else:
                await match_manager.move_locked(
                    match, user_id, int(action["column"]), broadcast=True, run_bot=False
                )
            await record_state(db, persisted, user_id, action, match.snapshot())
            if action.get("action") == "play_again":
                persisted.status = "active"
            await grant_game_participation_reward(db, user_id, match.id)
            if await settle_completed_match_progress(db, match, user_id):
                persisted.state = match.snapshot()
                persisted.status = "completed"
            await db.commit()
            match.version = persisted.version
        except Exception:
            await db.rollback()
            match.state = previous_state
            match.version = previous_version
            match.starting_player = previous_starting_player
            match.reward_granted = previous_reward_granted
            raise
    await realtime_bus.publish(
        match_channel(match.id),
        {
            "origin": get_settings().realtime_node_id,
            "payload": {
                "type": "state",
                "state": match.snapshot(),
                "version": match.version,
            },
        },
    )
    if (
        match.bot_player == match.state.current_player
        and not match.state.winner
        and not match.state.draw
    ):
        if match.bot_task is None or match.bot_task.done():
            match.bot_task = asyncio.create_task(run_connect_bot(match, user_id))


async def run_connect_bot(match: LiveMatch, initiator_id: int) -> None:
    """Take the bot turn off the request path so the human move stays responsive."""
    current_task = asyncio.current_task()
    try:
        await asyncio.sleep(0.55)
        async with session_factory() as db:
            async with match.lock:
                persisted = await db.scalar(
                    select(GameMatch).where(GameMatch.id == match.id).with_for_update()
                )
                if persisted is None:
                    return
                if persisted.version > match.version:
                    apply_connect_snapshot(match, persisted.state)
                    match.version = persisted.version
                if (
                    match.bot_player != match.state.current_player
                    or match.state.winner
                    or match.state.draw
                ):
                    return
                await match_manager.bot_move_locked(match, broadcast=False)
                await record_state(
                    db, persisted, initiator_id, {"action": "bot_move"}, match.snapshot()
                )
                if await settle_completed_match_progress(db, match, initiator_id):
                    persisted.status = "completed"
                await db.commit()
                match.version = persisted.version
                snapshot = match.snapshot()
            await match_manager.broadcast(match, {"type": "state", "state": snapshot, "bot": True})
            await realtime_bus.publish(
                match_channel(match.id),
                {
                    "origin": get_settings().realtime_node_id,
                    "payload": {"type": "state", "state": snapshot, "version": match.version},
                },
            )
    except asyncio.CancelledError:
        raise
    except Exception:
        logger.exception("connect_four_bot_turn_failed match_id=%s", match.id)
    finally:
        if match.bot_task is current_task:
            match.bot_task = None


@router.post("/games/matches/{match_id}/moves", response_model=MatchResponse)
async def play_move(
    match_id: str, payload: MoveRequest, user: CurrentUser, db: DbSession
) -> MatchResponse:
    match = match_manager.get(match_id)
    if match is None:
        raise HTTPException(status_code=404, detail="Match not found")
    try:
        await apply_connect_action(match, user.id, {"column": payload.column}, db)
    except IllegalMove as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except Exception as error:
        error_id = uuid4().hex[:12]
        logger.exception(
            "connect_four_action_failed error_id=%s match_id=%s user_id=%s",
            error_id,
            match.id,
            user.id,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Game error. Refresh and try again. Error reference: {error_id}",
        ) from error
    return match_response(match, user.id)


async def websocket_user(websocket: WebSocket) -> User | None:
    token = websocket.cookies.get(get_settings().session_cookie_name)
    authorization = websocket.headers.get("authorization", "")
    if not token and authorization.startswith("Bearer "):
        token = authorization[7:]
    if not token:
        return None
    import hashlib
    from datetime import UTC, datetime

    token_hash = hashlib.sha256(token.encode()).hexdigest()
    async with session_factory() as db:
        result = await db.execute(
            select(User)
            .join(Session, Session.user_id == User.id)
            .where(Session.token_hash == token_hash, Session.expires_at > datetime.now(UTC))
        )
        return result.scalar_one_or_none()


def websocket_origin_allowed(websocket: WebSocket) -> bool:
    origin = websocket.headers.get("origin")
    if not origin:
        return True
    settings = get_settings()
    if origin in settings.api_cors_origins:
        return True
    forwarded_host = websocket.headers.get("x-forwarded-host")
    forwarded_proto = websocket.headers.get("x-forwarded-proto", "https")
    if forwarded_host and origin == f"{forwarded_proto}://{forwarded_host}":
        return True
    scheme = "https" if websocket.url.scheme == "wss" else "http"
    return origin == f"{scheme}://{websocket.url.netloc}"


async def receive_socket_object(
    websocket: WebSocket, match_id: str, user_id: int
) -> dict[str, Any] | None:
    try:
        message = await websocket.receive_json()
    except WebSocketDisconnect:
        raise
    except Exception:
        logger.warning(
            "game_websocket_invalid_json match_id=%s user_id=%s",
            match_id,
            user_id,
            exc_info=True,
        )
        await websocket.send_json({"type": "error", "detail": "Send a valid JSON object"})
        return None
    if not isinstance(message, dict):
        await websocket.send_json({"type": "error", "detail": "Send a JSON object"})
        return None
    return message


@router.websocket("/games/matches/{match_id}/ws")
async def match_socket(websocket: WebSocket, match_id: str) -> None:
    if not websocket_origin_allowed(websocket):
        logger.warning("game_websocket_origin_rejected match_id=%s", match_id)
        await websocket.close(code=1008, reason="Origin is not allowed")
        return
    try:
        match = match_manager.get(match_id)
        if match is None:
            match, _ = await hydrate_match(match_id)
        user = await websocket_user(websocket)
    except Exception:
        error_id = uuid4().hex[:12]
        logger.exception(
            "connect_four_websocket_handshake_failed error_id=%s match_id=%s",
            error_id,
            match_id,
        )
        await websocket.close(code=1011, reason=f"Connection error: {error_id}")
        return
    if match is None or user is None:
        await websocket.close(code=1008, reason="Match or session is unavailable")
        return
    is_spectator = user.id not in match.player_ids
    await websocket.accept()
    match.sockets[websocket] = user.id
    relay_task = asyncio.create_task(
        relay_remote_events(websocket, match, user.id, is_spectator)
    )
    await websocket.send_json({"type": "state", "state": {**match.snapshot(None if is_spectator else user.id), "spectator": is_spectator}})
    await broadcast_spectator_count(match)
    try:
        while True:
            message = await receive_socket_object(websocket, match.id, user.id)
            if message is None:
                continue
            if is_spectator:
                await websocket.send_json({"type": "error", "detail": "Spectators cannot play moves"})
                continue
            if message.get("type") == "play_again":
                try:
                    async with session_factory() as db:
                        await apply_connect_action(
                            match, user.id, {"action": "play_again"}, db
                        )
                except IllegalMove as error:
                    await websocket.send_json({"type": "error", "detail": str(error)})
                except Exception:
                    error_id = uuid4().hex[:12]
                    logger.exception(
                        "connect_four_websocket_action_failed error_id=%s match_id=%s user_id=%s",
                        error_id,
                        match.id,
                        user.id,
                    )
                    await websocket.send_json(
                        {
                            "type": "error",
                            "detail": f"Game error. Refresh and try again. Error reference: {error_id}",
                        }
                    )
                continue
            if message.get("type") != "move" or not isinstance(message.get("column"), int):
                await websocket.send_json(
                    {"type": "error", "detail": "Send a move with a numeric column"}
                )
                continue
            try:
                async with session_factory() as db:
                    await apply_connect_action(
                        match, user.id, {"column": message["column"]}, db
                    )
            except IllegalMove as error:
                await websocket.send_json({"type": "error", "detail": str(error)})
                continue
            except Exception:
                error_id = uuid4().hex[:12]
                logger.exception(
                    "connect_four_websocket_action_failed error_id=%s match_id=%s user_id=%s",
                    error_id,
                    match.id,
                    user.id,
                )
                await websocket.send_json(
                    {
                        "type": "error",
                        "detail": f"Game error. Refresh and try again. Error reference: {error_id}",
                    }
                )
    except WebSocketDisconnect:
        match.sockets.pop(websocket, None)
    except Exception:
        logger.exception(
            "connect_four_websocket_failed match_id=%s user_id=%s", match.id, user.id
        )
    finally:
        relay_task.cancel()
        match.sockets.pop(websocket, None)
        await broadcast_spectator_count(match)


@router.post(
    "/games/sessions", response_model=GameSessionResponse, status_code=status.HTTP_201_CREATED
)
async def create_game_session(
    payload: GameSessionCreateRequest, user: CurrentUser, db: DbSession
) -> GameSessionResponse:
    room = await db.scalar(select(GameRoom).where(GameRoom.id == payload.room_id).with_for_update())
    if room is None or room.status != "open":
        raise HTTPException(status_code=404, detail="Room not available")
    if room.host_id != user.id:
        raise HTTPException(status_code=403, detail="Only the room host can start a match")
    joined = await db.scalar(
        select(RoomParticipant.id).where(
            RoomParticipant.room_id == room.id, RoomParticipant.user_id == user.id
        )
    )
    if joined is None:
        raise HTTPException(status_code=403, detail="Join the room before starting a match")
    game = await db.get(Game, room.game_id)
    game_type = game_type_for_name(game.name if game else "")
    if game_type not in GAME_TYPES:
        raise HTTPException(status_code=409, detail="This game is not playable yet")
    seats, player_ids, bot_players, player_names = await build_match_seats(
        room, game_type, user.id, db, payload.fill_with_bots
    )
    progress = await db.scalar(select(GameProgress).where(
        GameProgress.user_id == user.id, GameProgress.game_type == game_type
    ))
    game_level = progress.level if progress else 1
    game_streak = progress.current_streak if progress else 0
    difficulty = "thoughtful" if game_level >= 2 else room.bot_difficulty
    match = universal_matches.create(
        room.id,
        user.id,
        game_type,
        len(player_ids) if game_type in {"together", "abc-fast-slow", "csec-it-mock-exam"} and not payload.fill_with_bots else (room.max_players if game_type == "abc-fast-slow" else min(room.max_players, game_capacity(game_type))),
        player_ids=player_ids,
        bot_players=bot_players,
        player_names=player_names,
        bot_difficulty=difficulty,
    )
    match.state["game_level"] = game_level
    match.state["game_streak"] = game_streak
    if game_type == "abc-fast-slow":
        match.state["categories"] = list(room.abc_categories or ["Animal", "Place", "Food", "Thing"])
        match.state["majority_invalid"] = room.abc_majority_invalid
    room.status = "active"
    await create_persisted_match(db, match.id, room.id, game_type, user.id, match.state, seats)
    await db.commit()
    ensure_universal_timer(match)
    if universal_bot_needed(match):
        match.bot_task = asyncio.create_task(run_universal_bots(match, user.id))
    return universal_response(match, user.id, exam_admin=game_type == "csec-it-mock-exam" and user.name.strip().casefold() == "tyrese")


@router.get("/games/sessions/{match_id}", response_model=GameSessionResponse)
async def get_game_session(match_id: str, user: CurrentUser, spectate: bool = False) -> GameSessionResponse:
    match = universal_matches.get(match_id)
    if match is None:
        _, match = await hydrate_match(match_id)
    if match is None:
        raise HTTPException(status_code=404, detail="Game session not found")
    is_spectator = user.id not in match.player_ids
    if is_spectator and not spectate:
        raise HTTPException(status_code=403, detail="You are not a player in this match")
    ensure_universal_timer(match)
    return universal_response(match, None if is_spectator else user.id, spectator=is_spectator, exam_admin=user.name.strip().casefold() == "tyrese")


async def apply_universal_action(
    match: UniversalMatch,
    user_id: int,
    action: dict[str, Any],
    db: AsyncSession,
) -> None:
    """Apply one universal-game action with durable ordering and rollback."""
    kind = action.get("action")
    ephemeral = (
        match.game_type == "together" and kind == "input"
    ) or (
        match.game_type == "scribble" and kind == "stroke_segment"
    )
    if ephemeral:
        await universal_matches.action(match, user_id, action)
        payload: dict[str, Any]
        if match.game_type == "scribble":
            payload = {"type": "drawing_segment", "segment": match.state["strokes"][-1]}
        else:
            payload = {
                "type": "state",
                "state": deepcopy(match.state),
                "version": match.version,
            }
        await realtime_bus.publish(
            match_channel(match.id),
            {"origin": get_settings().realtime_node_id, "payload": payload},
        )
        return

    async with match.lock:
        previous_state = deepcopy(match.state)
        previous_version = match.version
        previous_reward_granted = match.reward_granted
        persisted = await db.scalar(
            select(GameMatch).where(GameMatch.id == match.id).with_for_update()
        )
        if persisted is None:
            raise ValueError("Persisted match not found")
        if persisted.version > match.version:
            match.state = deepcopy(persisted.state)
            match.version = persisted.version
        try:
            if kind == "play_again":
                await settle_completed_match_progress(db, match, user_id)
            await universal_matches.action_locked(
                match, user_id, action, broadcast=True, run_bots=False
            )
            await record_state(db, persisted, user_id, action, match.state)
            if kind == "play_again":
                persisted.status = "active"
            elif match.state.get("winner") is not None or match.state.get("draw", False):
                persisted.status = "completed"
            await grant_game_participation_reward(db, user_id, match.id)
            if await settle_completed_match_progress(db, match, user_id):
                persisted.state = deepcopy(match.state)
            await db.commit()
            match.version = persisted.version
        except Exception:
            await db.rollback()
            match.state = previous_state
            match.version = previous_version
            match.reward_granted = previous_reward_granted
            raise
    await realtime_bus.publish(
        match_channel(match.id),
        {
            "origin": get_settings().realtime_node_id,
            "payload": {
                "type": "state",
                "state": deepcopy(match.state),
                "version": match.version,
            },
        },
    )
    if universal_bot_needed(match) and (match.bot_task is None or match.bot_task.done()):
        match.bot_task = asyncio.create_task(run_universal_bots(match, user_id))


def universal_bot_needed(match: UniversalMatch) -> bool:
    bots = match.bot_players or ((match.bot_player,) if match.bot_player is not None else ())
    if not bots or match.state.get("winner") is not None or match.state.get("draw", False):
        return False
    if match.game_type == "abc-fast-slow":
        phase = match.state.get("phase")
        if phase in {"letter_picker", "letter_picker_running"}:
            return int(match.state.get("letter_chooser", -1)) in bots
        if phase == "answering":
            return any(not value for value in match.state.get("submitted", []))
        if phase == "voting":
            return any(not value for value in match.state.get("voted", [])) or any(
                not value for value in match.state.get("confirmed", [])
            )
        return False
    current = int(match.state.get("current_player", -1))
    return current in bots and (
        match.game_type != "scribble"
        or match.state.get("phase") == "choosing"
        or match.state.get("bot_draw_pending", False)
    )


async def run_universal_bots(match: UniversalMatch, initiator_id: int) -> None:
    """Process bot actions asynchronously, persisting each authoritative state."""
    current_task = asyncio.current_task()
    first = True
    try:
        while universal_bot_needed(match):
            if match.game_type == "ludo":
                delay = 2.05 if first else (0.95 if match.state.get("phase") == "roll" else 1.15)
            elif match.game_type == "abc-fast-slow":
                delay = 0.35
            else:
                delay = 0.7
            await asyncio.sleep(delay)
            first = False
            async with session_factory() as db:
                async with match.lock:
                    persisted = await db.scalar(
                        select(GameMatch).where(GameMatch.id == match.id).with_for_update()
                    )
                    if persisted is None:
                        return
                    if persisted.version > match.version:
                        match.state = deepcopy(persisted.state)
                        match.version = persisted.version
                    if not universal_bot_needed(match):
                        return
                    bot_action = await universal_matches.bot_action_locked(match, broadcast=False)
                    if bot_action is None:
                        return
                    await record_state(
                        db,
                        persisted,
                        initiator_id,
                        {"action": "bot", **bot_action},
                        match.state,
                    )
                    if await settle_completed_match_progress(db, match, initiator_id):
                        persisted.status = "completed"
                    await db.commit()
                    match.version = persisted.version
                    snapshot = deepcopy(match.state)
                await universal_matches.broadcast(match)
                await realtime_bus.publish(
                    match_channel(match.id),
                    {
                        "origin": get_settings().realtime_node_id,
                        "payload": {"type": "state", "state": snapshot, "version": match.version},
                    },
                )
    except asyncio.CancelledError:
        raise
    except Exception:
        logger.exception("universal_bot_turn_failed match_id=%s game=%s", match.id, match.game_type)
    finally:
        if match.bot_task is current_task:
            match.bot_task = None


def universal_deadline_action(
    match: UniversalMatch,
) -> tuple[int, dict[str, Any], float] | None:
    state = match.state
    if match.game_type == "abc-fast-slow":
        if state.get("phase") in {"letter_picker", "letter_picker_running"}:
            deadline = float(state.get("picker_deadline") or 0)
            return (int(state.get("letter_chooser", 0)), {"action": "picker_timeout"}, deadline)
        if state.get("phase") == "answering":
            deadline = float(state.get("deadline") or 0)
            return (0, {"action": "timeout"}, deadline)
    if match.game_type == "scribble" and state.get("phase") == "guessing":
        deadline = float(state.get("guess_deadline") or 0)
        drawer = int(state.get("current_drawer", 0))
        seat = next((value for value in match.player_ids.values() if value != drawer), -1)
        return (seat, {"action": "timeout"}, deadline)
    if match.game_type == "trivia" and state.get("phase") in {"question", "bot"}:
        deadline = float(state.get("deadline") or 0)
        return (int(state.get("current_player", 0)), {"answer": -1}, deadline)
    return None


async def universal_timer_worker(match: UniversalMatch) -> None:
    while universal_matches.get(match.id) is match:
        request = universal_deadline_action(match)
        if request is None:
            await asyncio.sleep(0.5)
            continue
        seat, action, deadline = request
        if deadline <= 0:
            await asyncio.sleep(0.25)
            continue
        remaining = deadline - time.time()
        if remaining > 0:
            await asyncio.sleep(min(remaining, 0.5))
            continue
        user_id = next(
            (candidate for candidate, candidate_seat in match.player_ids.items() if candidate_seat == seat),
            next(iter(match.player_ids), None),
        )
        if user_id is None:
            await asyncio.sleep(0.5)
            continue
        try:
            async with session_factory() as db:
                await apply_universal_action(match, user_id, action, db)
        except IllegalMove:
            await asyncio.sleep(0.25)
        except Exception:
            error_id = uuid4().hex[:12]
            logger.exception(
                "game_timer_failed error_id=%s match_id=%s game=%s",
                error_id,
                match.id,
                match.game_type,
            )
            await asyncio.sleep(1)


def ensure_universal_timer(match: UniversalMatch) -> None:
    if match.game_type not in {"abc-fast-slow", "scribble", "trivia"}:
        return
    if match.timer_task is None or match.timer_task.done():
        match.timer_task = asyncio.create_task(universal_timer_worker(match))


@router.post("/games/sessions/{match_id}/actions", response_model=GameSessionResponse)
async def game_session_action(
    match_id: str, payload: GameActionRequest, user: CurrentUser, db: DbSession
) -> GameSessionResponse:
    match = universal_matches.get(match_id)
    if match is None:
        _, match = await hydrate_match(match_id)
    if match is None:
        raise HTTPException(status_code=404, detail="Game session not found")
    user_id = user.id
    if user_id not in match.player_ids:
        raise HTTPException(status_code=403, detail="Spectators cannot play actions")
    try:
        await apply_universal_action(match, user_id, payload.action, db)
    except IllegalMove as error:
        logger.warning(
            "game_session_action_rejected match_id=%s user_id=%s action=%s error=%s",
            match_id,
            user_id,
            payload.action.get("action"),
            error,
        )
        raise HTTPException(status_code=409, detail=str(error)) from error
    except Exception as error:
        error_id = uuid4().hex[:12]
        logger.exception(
            "game_session_action_failed error_id=%s match_id=%s user_id=%s action=%s",
            error_id,
            match_id,
            user_id,
            payload.action.get("action"),
        )
        raise HTTPException(
            status_code=500,
            detail=f"Game error. Refresh and try again. Error reference: {error_id}",
        ) from error
    ensure_universal_timer(match)
    return universal_response(match, user_id, exam_admin=match.game_type == "csec-it-mock-exam" and user.name.strip().casefold() == "tyrese")


@router.websocket("/games/sessions/{match_id}/ws")
async def game_session_socket(websocket: WebSocket, match_id: str) -> None:
    if not websocket_origin_allowed(websocket):
        logger.warning("game_websocket_origin_rejected match_id=%s", match_id)
        await websocket.close(code=1008, reason="Origin is not allowed")
        return
    try:
        match = universal_matches.get(match_id)
        if match is None:
            _, match = await hydrate_match(match_id)
        user = await websocket_user(websocket)
    except Exception:
        error_id = uuid4().hex[:12]
        logger.exception(
            "game_session_websocket_handshake_failed error_id=%s match_id=%s",
            error_id,
            match_id,
        )
        await websocket.close(code=1011, reason=f"Connection error: {error_id}")
        return
    if match is None or user is None:
        await websocket.close(code=1008, reason="Match or session is unavailable")
        return
    is_spectator = user.id not in match.player_ids
    await websocket.accept()
    match.sockets[websocket] = user.id
    ensure_universal_timer(match)
    relay_task = asyncio.create_task(relay_remote_universal_events(websocket, match, user.id))
    await websocket.send_json({"type": "state", "match": match.snapshot(None if is_spectator else user.id, spectator=is_spectator, exam_admin=user.name.strip().casefold() == "tyrese")})
    await broadcast_spectator_count(match)
    try:
        while True:
            message = await receive_socket_object(websocket, match.id, user.id)
            if message is None:
                continue
            if is_spectator:
                await websocket.send_json({"type": "error", "detail": "Spectators cannot play actions"})
                continue
            if message.get("type") != "action" or not isinstance(message.get("action"), dict):
                await websocket.send_json({"type": "error", "detail": "Send an action object"})
                continue
            try:
                async with session_factory() as db:
                    await apply_universal_action(match, user.id, message["action"], db)
            except IllegalMove as error:
                logger.warning(
                    "game_session_websocket_action_rejected match_id=%s user_id=%s action=%s error=%s",
                    match_id,
                    user.id,
                    message["action"].get("action"),
                    error,
                )
                await websocket.send_json({"type": "error", "detail": str(error)})
                continue
            except Exception:
                error_id = uuid4().hex[:12]
                logger.exception(
                    "game_session_websocket_action_failed error_id=%s match_id=%s user_id=%s action=%s",
                    error_id,
                    match_id,
                    user.id,
                    message["action"].get("action"),
                )
                await websocket.send_json(
                    {
                        "type": "error",
                        "detail": f"Game error. Refresh and try again. Error reference: {error_id}",
                    }
                )
                continue
    except WebSocketDisconnect:
        match.sockets.pop(websocket, None)
    except Exception:
        logger.exception(
            "game_session_websocket_failed match_id=%s user_id=%s", match.id, user.id
        )
    finally:
        relay_task.cancel()
        match.sockets.pop(websocket, None)
        await broadcast_spectator_count(match)


@router.get("/games/winners", response_model=list[dict[str, object]])
async def list_winners(
    user: CurrentUser, db: DbSession, page: int = 1, limit: int = 10
) -> list[dict[str, object]]:
    del user
    page = max(page, 1)
    limit = min(max(limit, 1), 100)
    recent_wins = (
        await db.execute(
            select(
                RewardLedger.id,
                RewardLedger.user_id,
                User.name,
                User.avatar_url,
                RewardLedger.xp,
                RewardLedger.match_id,
                RewardLedger.created_at,
            )
            .join(User, User.id == RewardLedger.user_id)
            .where(RewardLedger.kind == "game_win", User.is_guest.is_(False))
            .order_by(RewardLedger.created_at.desc(), RewardLedger.id.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        )
    ).all()
    result: list[dict[str, object]] = []
    for position, row in enumerate(recent_wins, start=(page - 1) * limit + 1):
        # Older reward rows may not have a persisted match id. Never pass a
        # NULL identity to AsyncSession.get(), which emits a SQLAlchemy
        # warning and can become an error in a future release.
        game_name = row.match_id
        match = await db.get(GameMatch, game_name) if game_name else None
        game_label = (match.game_type.replace("-", " ").title() if match else "Game")
        progress = await db.scalar(select(GameProgress).where(
            GameProgress.user_id == row.user_id, GameProgress.game_type == (match.game_type if match else "")
        )) if match else None
        result.append(
            {
                "position": position,
                "name": row.name,
                "avatar_url": row.avatar_url,
                "points": int(row.xp or 0),
                "match_points": int(row.xp or 0),
                "wins": 1,
                "game": game_label,
                "level": progress.level if progress else 1,
                "streak": progress.current_streak if progress else 1,
                "created_at": row.created_at,
            }
        )
    return result


def leaderboard_query(
    period: str,
    period_start: datetime | None = None,
    period_end: datetime | None = None,
):
    """Return members and the XP earned in the requested ranking window."""
    member_filter = User.is_guest.is_(False)
    if period == "all":
        return select(User, User.xp.label("ranking_xp")).where(member_filter)

    start = period_start or leaderboard_period_start(period)
    reward_window = [RewardLedger.created_at >= start]
    checkin_window = [CheckIn.created_at >= start, CheckIn.completed.is_(True)]
    challenge_window = [ChallengeCompletion.created_at >= start]
    if period_end is not None:
        reward_window.append(RewardLedger.created_at < period_end)
        checkin_window.append(CheckIn.created_at < period_end)
        challenge_window.append(ChallengeCompletion.created_at < period_end)
    reward_totals = (
        select(
            RewardLedger.user_id,
            func.coalesce(func.sum(RewardLedger.xp), 0).label("reward_xp"),
        )
        .where(*reward_window)
        .group_by(RewardLedger.user_id)
        .subquery()
    )
    checkin_totals = (
        select(
            CheckIn.user_id,
            (func.count(CheckIn.id) * 25).label("checkin_xp"),
        )
        .where(*checkin_window)
        .group_by(CheckIn.user_id)
        .subquery()
    )
    challenge_totals = (
        select(
            ChallengeCompletion.user_id,
            func.coalesce(func.sum(ChallengeCompletion.xp_awarded), 0).label("challenge_xp"),
        )
        .where(*challenge_window)
        .group_by(ChallengeCompletion.user_id)
        .subquery()
    )
    ranking_xp = (
        func.coalesce(reward_totals.c.reward_xp, 0)
        + func.coalesce(checkin_totals.c.checkin_xp, 0)
        + func.coalesce(challenge_totals.c.challenge_xp, 0)
    ).label("ranking_xp")
    return (
        select(User, ranking_xp)
        .outerjoin(reward_totals, reward_totals.c.user_id == User.id)
        .outerjoin(checkin_totals, checkin_totals.c.user_id == User.id)
        .outerjoin(challenge_totals, challenge_totals.c.user_id == User.id)
        .where(member_filter, ranking_xp > 0)
    )


def public_asset_url(value: str | None, public_url: str) -> str | None:
    if not value:
        return None
    if value.startswith(("http://", "https://")):
        return value
    return f"{public_url.rstrip('/')}/{value.lstrip('/')}"


@router.get("/leaderboard", response_model=list[LeaderboardEntry])
async def leaderboard(
    user: CurrentUser, db: DbSession, period: str = "week", page: int = 1, limit: int = 10
) -> list[LeaderboardEntry]:
    if period not in {"day", "week", "month", "all"}:
        raise HTTPException(status_code=422, detail="Invalid leaderboard period")
    page = max(page, 1)
    limit = min(max(limit, 1), 100)
    query = leaderboard_query(period)
    rows = (
        await db.execute(
            query.order_by(query.selected_columns.ranking_xp.desc(), User.created_at.asc())
            .offset((page - 1) * limit)
            .limit(limit)
        )
    ).all()
    return [
        LeaderboardEntry(
            rank=(page - 1) * limit + index,
            user=user_response(member).model_copy(update={"xp": int(ranking_xp)}),
        )
        for index, (member, ranking_xp) in enumerate(rows, start=1)
    ]


@router.get("/leaderboard/me", response_model=LeaderboardEntry)
async def leaderboard_me(
    user: CurrentUser, db: DbSession, period: str = "week"
) -> LeaderboardEntry:
    if period not in {"day", "week", "month", "all"}:
        raise HTTPException(status_code=422, detail="Invalid leaderboard period")
    if user.is_guest:
        raise HTTPException(status_code=403, detail="Temporary guest players are not ranked")
    query = leaderboard_query(period)
    current_row = (await db.execute(query.where(User.id == user.id))).first()
    current_xp = int(current_row[1]) if current_row else 0
    ranking = query.subquery()
    rank = (
        await db.scalar(
            select(func.count()).select_from(ranking).where(ranking.c.ranking_xp > current_xp)
        )
        or 0
    ) + 1
    return LeaderboardEntry(
        rank=rank,
        user=user_response(user).model_copy(update={"xp": current_xp}),
    )


@router.post("/community-applications", response_model=CommunityApplicationResponse, status_code=status.HTTP_201_CREATED)
async def create_community_application(
    payload: CommunityApplicationCreateRequest,
    db: DbSession,
) -> CommunityApplicationResponse:
    if not payload.consent:
        raise HTTPException(status_code=422, detail="Please consent to being contacted")
    if payload.website and payload.website.strip():
        # Honeypot: acknowledge automated submissions without storing them.
        raise HTTPException(status_code=422, detail="Please try again")
    email = str(payload.email).lower()
    existing = await db.scalar(
        select(CommunityApplication).where(
            CommunityApplication.email == email,
            CommunityApplication.status == "pending",
        )
    )
    if existing:
        raise HTTPException(status_code=409, detail="An application for this email is already under review")
    application = CommunityApplication(
        name=payload.name.strip(),
        email=email,
        phone=payload.phone.strip() if payload.phone else None,
        message=payload.message.strip(),
    )
    db.add(application)
    await db.commit()
    await db.refresh(application)
    await notify_admins_of_application(application, db)
    return community_application_response(application)


@router.get("/community-applications/invite/{token}", include_in_schema=False)
async def use_community_application_invite(token: str, db: DbSession) -> RedirectResponse:
    application = await db.scalar(
        select(CommunityApplication).where(
            CommunityApplication.invite_token_hash == invite_token_hash(token),
            CommunityApplication.status == "approved",
        )
    )
    settings = get_settings()
    now = datetime.now(UTC)
    if (
        application is None
        or application.invite_used_at is not None
        or application.invite_expires_at is None
        or application.invite_expires_at <= now
        or not settings.whatsapp_group_invite_url
    ):
        raise HTTPException(status_code=404, detail="This community invitation is no longer available")
    application.invite_used_at = now
    await db.commit()
    return RedirectResponse(settings.whatsapp_group_invite_url, status_code=status.HTTP_303_SEE_OTHER)


@router.get("/admin/community-applications", response_model=list[CommunityApplicationResponse])
async def admin_community_applications(
    admin: CurrentAdmin,
    db: DbSession,
    page: int = 1,
    limit: int = 20,
    application_status: str | None = None,
) -> list[CommunityApplicationResponse]:
    if admin.role not in STAFF_ROLES:
        raise HTTPException(status_code=403, detail="Staff access required")
    page = max(page, 1)
    limit = min(max(limit, 1), 100)
    query = select(CommunityApplication).order_by(CommunityApplication.created_at.desc())
    if application_status:
        if application_status not in {"pending", "approved", "rejected"}:
            raise HTTPException(status_code=422, detail="Invalid application status")
        query = query.where(CommunityApplication.status == application_status)
    rows = (await db.scalars(query.offset((page - 1) * limit).limit(limit))).all()
    return [community_application_response(row) for row in rows]


async def review_community_application(
    application_id: int,
    payload: CommunityApplicationUpdateRequest,
    admin: User,
    db: AsyncSession,
) -> CommunityApplicationResponse:
    if not can_review_community_applications(admin):
        raise HTTPException(status_code=403, detail="Application approval access required")
    application = await db.get(CommunityApplication, application_id)
    if application is None:
        raise HTTPException(status_code=404, detail="Community application not found")
    application.status = payload.status
    application.admin_note = payload.admin_note.strip() if payload.admin_note else None
    application.reviewed_by = admin.id
    application.reviewed_at = datetime.now(UTC)
    token: str | None = None
    if payload.status == "approved":
        token = secrets.token_urlsafe(32)
        application.invite_token_hash = invite_token_hash(token)
        application.invite_expires_at = datetime.now(UTC) + timedelta(days=7)
        application.invite_used_at = None
    else:
        application.invite_token_hash = None
        application.invite_expires_at = None
        application.invite_used_at = None
        application.email_sent_at = None
    await db.commit()
    if token is not None and await send_application_invite(application, token):
        application.email_sent_at = datetime.now(UTC)
        await db.commit()
    await db.refresh(application)
    return community_application_response(application)


@router.patch("/admin/community-applications/{application_id}", response_model=CommunityApplicationResponse)
async def update_community_application(
    application_id: int,
    payload: CommunityApplicationUpdateRequest,
    admin: CurrentAdmin,
    db: DbSession,
) -> CommunityApplicationResponse:
    return await review_community_application(application_id, payload, admin, db)


@router.post("/admin/community-applications/{application_id}/resend", response_model=CommunityApplicationResponse)
async def resend_community_application(
    application_id: int,
    admin: CurrentAdmin,
    db: DbSession,
) -> CommunityApplicationResponse:
    if not can_review_community_applications(admin):
        raise HTTPException(status_code=403, detail="Application approval access required")
    application = await db.get(CommunityApplication, application_id)
    if application is None or application.status != "approved":
        raise HTTPException(status_code=409, detail="Only approved applications can receive an invite")
    token = secrets.token_urlsafe(32)
    application.invite_token_hash = invite_token_hash(token)
    application.invite_expires_at = datetime.now(UTC) + timedelta(days=7)
    application.invite_used_at = None
    await db.commit()
    if await send_application_invite(application, token):
        application.email_sent_at = datetime.now(UTC)
        await db.commit()
    await db.refresh(application)
    return community_application_response(application)


@router.get("/admin/bug-reports", response_model=list[BugReportResponse])
async def admin_bug_reports(
    admin: CurrentAdmin,
    db: DbSession,
    page: int = 1,
    limit: int = 20,
    report_status: str | None = None,
) -> list[BugReportResponse]:
    del admin
    page = max(page, 1)
    limit = min(max(limit, 1), 100)
    query = (
        select(BugReport, User)
        .join(User, User.id == BugReport.user_id)
        .order_by(BugReport.created_at.desc())
    )
    if report_status:
        if report_status not in {"open", "in_progress", "resolved", "closed"}:
            raise HTTPException(status_code=422, detail="Invalid bug report status")
        query = query.where(BugReport.status == report_status)
    rows = (await db.execute(query.offset((page - 1) * limit).limit(limit))).all()
    return [bug_report_response(report, reporter) for report, reporter in rows]


@router.get("/admin/dashboard", response_model=AdminDashboardResponse)
async def admin_dashboard(
    admin: CurrentAdmin,
    db: DbSession,
) -> AdminDashboardResponse:
    del admin
    total_members = await db.scalar(
        select(func.count(User.id)).where(User.is_guest.is_(False))
    )
    pending_members = await db.scalar(
        select(func.count(User.id)).where(
            User.is_guest.is_(False), User.is_approved.is_(False)
        )
    )
    open_bug_reports = await db.scalar(
        select(func.count(BugReport.id))
        .join(User, User.id == BugReport.user_id)
        .where(BugReport.status.in_(("open", "in_progress")))
    )
    pending_quotes = await db.scalar(
        select(func.count(Quote.id)).where(Quote.approval_status == "pending")
    )
    active_rooms = await db.scalar(
        select(func.count(GameRoom.id)).where(GameRoom.status.in_(("open", "active")))
    )
    total_quotes = await db.scalar(select(func.count(Quote.id)))
    pending_community_applications = await db.scalar(
        select(func.count(CommunityApplication.id)).where(
            CommunityApplication.status == "pending"
        )
    )
    return AdminDashboardResponse(
        total_members=total_members or 0,
        pending_members=pending_members or 0,
        open_bug_reports=open_bug_reports or 0,
        pending_quotes=pending_quotes or 0,
        active_rooms=active_rooms or 0,
        total_quotes=total_quotes or 0,
        pending_community_applications=pending_community_applications or 0,
    )


@router.patch("/admin/bug-reports/{report_id}", response_model=BugReportResponse)
async def update_bug_report(
    report_id: int,
    payload: BugReportUpdateRequest,
    admin: CurrentAdmin,
    db: DbSession,
) -> BugReportResponse:
    report = await db.get(BugReport, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Bug report not found")
    reporter = await db.get(User, report.user_id) if report.user_id else None
    if reporter is None:
        raise HTTPException(status_code=404, detail="Report owner not found")
    report.status = payload.status
    report.admin_note = payload.admin_note.strip() if payload.admin_note else None
    await db.commit()
    await db.refresh(report)
    return bug_report_response(report, reporter)


@router.get("/admin/users", response_model=list[UserResponse])
async def admin_users(
    admin: CurrentAdmin,
    db: DbSession,
    page: int = 1,
    limit: int = 20,
    search: str | None = None,
) -> list[UserResponse]:
    del admin
    page = max(page, 1)
    limit = min(max(limit, 1), 100)
    query = select(User).order_by(User.created_at.desc())
    if search and search.strip():
        term = f"%{search.strip()}%"
        query = query.where((User.name.ilike(term)) | (User.email.ilike(term)))
    users = (await db.scalars(query.offset((page - 1) * limit).limit(limit))).all()
    return [user_response(member) for member in users]


@router.post("/admin/notifications/weekly-performers", response_model=AdminNotificationResponse)
async def send_weekly_performer_notification(
    admin: CurrentAdmin,
    db: DbSession,
    start_date: date | None = None,
    end_date: date | None = None,
) -> AdminNotificationResponse:
    if not can_manage_content(admin):
        raise HTTPException(status_code=403, detail="Staff access required")
    if (start_date is None) != (end_date is None):
        raise HTTPException(status_code=422, detail="Provide both start_date and end_date")
    if start_date is None:
        period_start = leaderboard_period_start("week") - timedelta(days=7)
        period_end = period_start + timedelta(days=7)
    else:
        if start_date >= end_date:
            raise HTTPException(status_code=422, detail="end_date must be after start_date")
        period_start = datetime.combine(start_date, datetime.min.time(), tzinfo=UTC)
        period_end = datetime.combine(end_date + timedelta(days=1), datetime.min.time(), tzinfo=UTC)
    query = leaderboard_query("week", period_start=period_start, period_end=period_end)
    rows = (
        await db.execute(
            query.order_by(query.selected_columns.ranking_xp.desc(), User.created_at.asc()).limit(3)
        )
    ).all()
    settings = get_settings()
    winners = [
        (
            member.id,
            member.name,
            int(ranking_xp),
            public_asset_url(member.avatar_url, settings.public_app_url),
        )
        for member, ranking_xp in rows
    ]
    recipients = (
        await db.scalars(
            select(User).where(
                User.is_approved.is_(True),
                User.is_guest.is_(False),
                User.email_notifications_enabled.is_(True),
            )
        )
    ).all()
    if not winners or not recipients:
        return AdminNotificationResponse(
            notification="weekly_performers",
            sent=0,
            failed=0,
            recipients=len(recipients),
            period_start=period_start.date(),
            winners=[name for _, name, _, _ in winners],
        )
    html, text = weekly_performers_email(
        winners=winners,
        period_start=period_start.date(),
        period_end=(period_end - timedelta(days=1)).date(),
        action_url=f"{settings.public_app_url.rstrip('/')}/leaderboard",
    )
    results = await asyncio.gather(
        *(
            send_transactional_email(
                recipient=recipient.email,
                subject="Last week’s Safe Space Saturdays leaders",
                html=html,
                text=text,
            )
            for recipient in recipients
        ),
        return_exceptions=True,
    )
    sent = sum(result is True for result in results)
    return AdminNotificationResponse(
        notification="weekly_performers",
        sent=sent,
        failed=len(results) - sent,
        recipients=len(recipients),
        period_start=period_start.date(),
        winners=[name for _, name, _, _ in winners],
    )


@router.post("/admin/notifications/daily-checkin", response_model=AdminNotificationResult)
async def send_daily_checkin_notification(
    admin: CurrentAdmin, db: DbSession
) -> AdminNotificationResult:
    if not can_manage_content(admin):
        raise HTTPException(status_code=403, detail="Staff access required")
    day_name = datetime.now(ZoneInfo("America/Jamaica")).strftime("%A")
    recipients = (
        await db.scalars(
            select(User).where(
                User.is_approved.is_(True),
                User.is_guest.is_(False),
                User.email_notifications_enabled.is_(True),
            )
        )
    ).all()
    if not recipients:
        return AdminNotificationResult(
            notification="daily_checkin",
            sent=0,
            failed=0,
            recipients=0,
            message=DAILY_CHECKIN_MESSAGES[day_name],
        )
    settings = get_settings()
    html, text = daily_checkin_email(
        day_name=day_name,
        action_url=f"{settings.public_app_url.rstrip('/')}/check-in",
    )
    results = await asyncio.gather(
        *(
            send_transactional_email(
                recipient=recipient.email,
                subject=f"A gentle {day_name} check-in from Safe Space Saturdays",
                html=html,
                text=text,
            )
            for recipient in recipients
        ),
        return_exceptions=True,
    )
    sent = sum(result is True for result in results)
    return AdminNotificationResult(
        notification="daily_checkin",
        sent=sent,
        failed=len(results) - sent,
        recipients=len(recipients),
        message=DAILY_CHECKIN_MESSAGES[day_name],
    )


@router.patch("/admin/users/{user_id}", response_model=UserResponse)
async def update_admin_user(
    user_id: int,
    payload: AdminUserUpdateRequest,
    admin: CurrentAdmin,
    db: DbSession,
) -> UserResponse:
    if not can_manage_roles(admin):
        raise HTTPException(status_code=403, detail="Only super administrators can manage roles and approvals")
    member = await db.get(User, user_id)
    if member is None:
        raise HTTPException(status_code=404, detail="User not found")
    if (
        payload.role is None
        and payload.is_approved is None
        and payload.email_notifications_enabled is None
    ):
        raise HTTPException(status_code=422, detail="Provide a user setting to change")
    if member.id == admin.id and payload.role not in {None, "admin", "super_admin"}:
        raise HTTPException(status_code=400, detail="You cannot remove your own admin access")
    if payload.role is not None:
        member.role = payload.role
    if payload.is_approved is not None:
        member.is_approved = payload.is_approved
    if payload.email_notifications_enabled is not None:
        member.email_notifications_enabled = payload.email_notifications_enabled
    await db.commit()
    await db.refresh(member)
    return user_response(member)


@router.post("/admin/users/{user_id}/password-reset", status_code=status.HTTP_204_NO_CONTENT)
async def reset_user_password(
    user_id: int,
    payload: AdminPasswordResetRequest,
    admin: CurrentAdmin,
    db: DbSession,
) -> None:
    del admin
    member = await db.get(User, user_id)
    if member is None:
        raise HTTPException(status_code=404, detail="User not found")
    member.password_hash = hash_password(payload.password)
    await db.execute(delete(Session).where(Session.user_id == user_id))
    await db.commit()


@router.get("/admin/quotes", response_model=list[QuoteResponse])
async def admin_quotes(
    admin: CurrentAdmin,
    db: DbSession,
    page: int = 1,
    limit: int = 20,
    category: str | None = None,
) -> list[QuoteResponse]:
    if not can_manage_content(admin) and admin.role != "moderator":
        raise HTTPException(status_code=403, detail="Content moderation access required")
    page = max(page, 1)
    limit = min(max(limit, 1), 100)
    query = select(Quote).order_by(Quote.created_at.desc())
    if category:
        query = query.where(Quote.category == category)
    quotes = (await db.scalars(query.offset((page - 1) * limit).limit(limit))).all()
    return [QuoteResponse.model_validate(quote) for quote in quotes]


@router.post("/admin/announcements", response_model=AnnouncementResponse, status_code=status.HTTP_201_CREATED)
async def create_announcement(
    admin: CurrentAdmin,
    db: DbSession,
    title: Annotated[str, Form(min_length=3, max_length=160)],
    body: Annotated[str, Form(min_length=3, max_length=1000)],
    cta_label: Annotated[str | None, Form(max_length=80)] = None,
    cta_path: Annotated[str | None, Form(max_length=200)] = None,
    image: Annotated[UploadFile | None, File()] = None,
) -> AnnouncementResponse:
    if not can_manage_roles(admin):
        raise HTTPException(status_code=403, detail="Only administrators can post announcements")
    image_url = await save_post_image(image) if image else None
    announcement = Announcement(
        author_id=admin.id, title=title.strip(), body=body.strip(),
        cta_label=cta_label.strip() if cta_label else None,
        cta_path=cta_path.strip() if cta_path else None, image_url=image_url,
    )
    db.add(announcement)
    await db.commit()
    await db.refresh(announcement)
    recipients = (await db.scalars(select(User).where(
        User.email_notifications_enabled.is_(True), User.is_approved.is_(True), User.is_guest.is_(False)
    ))).all()
    settings = get_settings()
    public_image = image_url if not image_url or image_url.startswith("http") else f"{settings.public_app_url.rstrip('/')}{image_url}"
    image_html = f'<img src="{escape(public_image)}" alt="" style="width:100%;max-width:640px;border-radius:12px;margin:16px 0;">' if public_image else ""
    for recipient in recipients:
        cta_html = (
            f'<a href="{escape(settings.public_app_url.rstrip("/") + (cta_path or "/community"))}" '
            'style="display:inline-block;padding:12px 18px;border-radius:999px;background:#566946;color:#fffdf8;'
            'font-weight:700;text-decoration:none;">'
            f'{escape(cta_label or "Open Safe Space Saturdays")}</a>'
            if cta_path else ""
        )
        await send_transactional_email(
            recipient=recipient.email, subject=title.strip(),
            html=(
                '<div style="margin:0 auto;max-width:640px;padding:32px 24px;background:#f9f5ed;'
                'font-family:Arial,sans-serif;color:#18362a;">'
                '<div style="padding:28px;border:1px solid #e9e1d5;border-radius:22px;background:#fffdf8;">'
                '<p style="margin:0 0 18px;color:#566946;font-size:12px;font-weight:700;letter-spacing:2px;'
                'text-transform:uppercase;">Safe Space Saturdays</p>'
                f'<h1 style="margin:0;color:#18362a;font-family:Georgia,serif;font-size:32px;line-height:1.15;">{escape(title.strip())}</h1>'
                f'{image_html}<p style="color:#5c625e;font-size:16px;line-height:1.6;">{escape(body.strip())}</p>'
                f'<p style="margin:24px 0 0;">{cta_html}</p>'
                '</div></div>'
            ),
            text=f"{title.strip()}\n\n{body.strip()}",
        )
    return AnnouncementResponse.model_validate(announcement)


@router.post("/admin/quotes", response_model=QuoteResponse, status_code=status.HTTP_201_CREATED)
async def admin_create_quote(
    payload: AdminQuoteCreateRequest, admin: CurrentAdmin, db: DbSession
) -> QuoteResponse:
    if not can_manage_content(admin):
        raise HTTPException(status_code=403, detail="Content management access required")
    if payload.is_featured:
        await db.execute(update(Quote).values(is_featured=False))
    quote = Quote(**payload.model_dump())
    db.add(quote)
    await db.commit()
    await db.refresh(quote)
    return QuoteResponse.model_validate(quote)


@router.patch("/admin/quotes/{quote_id}", response_model=QuoteResponse)
async def admin_update_quote(
    quote_id: int,
    payload: AdminQuoteUpdateRequest,
    admin: CurrentAdmin,
    db: DbSession,
) -> QuoteResponse:
    if not can_manage_content(admin) and admin.role != "moderator":
        raise HTTPException(status_code=403, detail="Content moderation access required")
    quote = await db.get(Quote, quote_id)
    if quote is None:
        raise HTTPException(status_code=404, detail="Quote not found")
    if payload.is_featured:
        await db.execute(update(Quote).where(Quote.id != quote_id).values(is_featured=False))
    for key, value in payload.model_dump().items():
        setattr(quote, key, value)
    await db.commit()
    await db.refresh(quote)
    return QuoteResponse.model_validate(quote)


@router.delete("/admin/quotes/{quote_id}", status_code=status.HTTP_204_NO_CONTENT)
async def admin_delete_quote(quote_id: int, admin: CurrentAdmin, db: DbSession) -> None:
    if not can_manage_content(admin):
        raise HTTPException(status_code=403, detail="Content management access required")
    quote = await db.get(Quote, quote_id)
    if quote is None:
        raise HTTPException(status_code=404, detail="Quote not found")
    if quote.is_featured:
        raise HTTPException(
            status_code=409,
            detail="Choose another featured quote before deleting this one",
        )
    await db.delete(quote)
    await db.commit()
