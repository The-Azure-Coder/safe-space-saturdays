import asyncio
import io
import secrets
from collections import Counter
from collections.abc import Iterable
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Annotated
from uuid import uuid4

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
from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import get_session, session_factory
from app.games.connect_four import ConnectFourState, IllegalMove
from app.games.manager import LiveMatch, match_manager
from app.games.multi import (
    GAME_TYPES,
    normalise_bingo_state,
    normalise_domino_state,
    normalise_ludo_state,
)
from app.games.persistence import create_persisted_match, record_state
from app.games.realtime import realtime_bus
from app.games.scribble import normalise_scribble_state
from app.games.trivia import normalise_trivia_state
from app.games.universal import UniversalMatch, universal_matches
from app.models import (
    BugReport,
    CheckIn,
    Challenge,
    ChallengeCompletion,
    Comment,
    Game,
    GameMatch,
    GameMatchPlayer,
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
    AdminPasswordResetRequest,
    AdminQuoteCreateRequest,
    AdminQuoteUpdateRequest,
    AdminUserUpdateRequest,
    AuthResponse,
    BugReportCreateRequest,
    BugReportResponse,
    BugReportUpdateRequest,
    ChangePasswordRequest,
    ChallengeCompleteRequest,
    ChallengeResponse,
    ChallengesResponse,
    CheckInRequest,
    CheckInResponse,
    CommentCreateRequest,
    CommentResponse,
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
DbSession = Annotated[AsyncSession, Depends(get_session)]
CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentAdmin = Annotated[User, Depends(get_current_admin)]

STAFF_ROLES = {"admin", "super_admin", "manager", "moderator"}


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


def can_manage_content(user: User) -> bool:
    return user.role in {"admin", "super_admin", "manager"}


def match_response(match: LiveMatch, user_id: int | None = None) -> MatchResponse:
    return MatchResponse.model_validate(match.snapshot(user_id))


def universal_response(match: UniversalMatch, user_id: int | None = None) -> GameSessionResponse:
    return GameSessionResponse.model_validate(match.snapshot(user_id))


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
        range(1, player_count if row.game_type in {"ludo", "dominoes", "scribble"} else 2)
    )
    match = UniversalMatch(
        id=row.id,
        room_id=row.room_id,
        game_type=row.game_type,
        state=row.state,
        player_ids=player_ids,
        bot_player=resolved_bot_players[0] if resolved_bot_players else None,
        bot_players=resolved_bot_players,
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


async def relay_remote_events(websocket: WebSocket, match_id: str) -> None:
    async for message in realtime_bus.subscribe(match_channel(match_id)):
        if message.get("origin") != get_settings().realtime_node_id:
            await websocket.send_json(message["payload"])


async def relay_remote_universal_events(
    websocket: WebSocket, match: UniversalMatch, user_id: int
) -> None:
    async for message in realtime_bus.subscribe(match_channel(match.id)):
        if message.get("origin") != get_settings().realtime_node_id:
            await websocket.send_json({"type": "state", "match": match.snapshot(user_id)})


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


async def grant_completed_game_rewards(
    db: AsyncSession,
    player_ids: dict[int, int],
    match_id: str,
    winner: int | None,
) -> None:
    """Reconcile rewards for every human when a match reaches a terminal state."""
    for user_id, seat in player_ids.items():
        await grant_game_participation_reward(db, user_id, match_id)
        if winner is not None and seat == winner:
            await grant_game_win_reward(db, user_id, match_id)


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
        **{field: getattr(user, field) for field in UserResponse.model_fields if field != "is_online"},
        "is_online": is_user_online(user),
    }
    if user.is_guest and user.email.endswith("@guest.invalid"):
        values["email"] = f"guest-{user.id}@guests.safespacesaturdays.app"
    return UserResponse.model_validate(values)


def game_capacity(game_name: str) -> int:
    normalized = game_name.strip().lower()
    if normalized in {"connect four", "connect-four", "trivia", "trivia battle"}:
        return 2
    if normalized in {"ludo", "dominoes", "block dominoes", "scribble", "scribble game"}:
        return 4
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
    count = min(room.max_players, game_capacity(game_type))
    if len(participants) > count:
        raise HTTPException(
            status_code=409, detail="This room has too many players for the selected game"
        )
    if not fill_with_bots and len(participants) < count:
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
    for seat_index in range(count):
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
                is_approved=registered_count < 20,
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
    is_approved = registered_count < 20
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
    latest = await db.scalar(
        select(CheckIn)
        .where(CheckIn.user_id == user.id)
        .order_by(CheckIn.created_at.desc())
        .limit(1)
    )
    quote = await db.scalar(
        select(Quote).where(Quote.is_featured.is_(True)).order_by(Quote.id).limit(1)
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
    user: CurrentUser, db: DbSession, page: int = 1, limit: int = 20
) -> list[PostResponse]:
    page = max(page, 1)
    limit = min(max(limit, 1), 100)
    rows = (
        await db.scalars(
            select(Post)
            .where(Post.is_hidden.is_(False))
            .order_by(Post.created_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        )
    ).all()
    return [await post_out(post, user.id, db) for post in rows]


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
    post = Post(user_id=user.id, text=payload.text.strip())
    db.add(post)
    await db.commit()
    await db.refresh(post)
    await grant_community_post_reward(db, user.id, post.id)
    await db.commit()
    return await post_out(post, user.id, db)


@router.post("/community/posts/from-quote/{quote_id}", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
async def share_quote_to_community(quote_id: int, user: CurrentUser, db: DbSession) -> PostResponse:
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
    )


@router.get("/games", response_model=list[GameResponse])
async def list_games(
    user: CurrentUser, db: DbSession, page: int = 1, limit: int = 20
) -> list[GameResponse]:
    page = max(page, 1)
    limit = min(max(limit, 1), 100)
    return [
        GameResponse.model_validate(game)
        for game in (
            await db.scalars(
                select(Game)
                .order_by(Game.is_featured.desc(), Game.id)
                .offset((page - 1) * limit)
                .limit(limit)
            )
        ).all()
    ]


async def room_out(room: GameRoom, user_id: int, db: AsyncSession) -> RoomResponse:
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
        fill_with_bots=room.fill_with_bots,
        invite_token=room.invite_token if participant is not None else None,
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
    return [await room_out(room, user.id, db) for room in rooms]


@router.post("/games/rooms", response_model=RoomResponse, status_code=status.HTTP_201_CREATED)
async def create_room(payload: RoomCreateRequest, user: CurrentUser, db: DbSession) -> RoomResponse:
    game = await db.get(Game, payload.game_id)
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")
    if payload.max_players > game_capacity(game.name):
        raise HTTPException(
            status_code=422,
            detail=f"{game.name} supports at most {game_capacity(game.name)} players",
        )
    room = GameRoom(
        game_id=payload.game_id,
        host_id=user.id,
        name=payload.name.strip(),
        max_players=payload.max_players,
        fill_with_bots=payload.fill_with_bots,
        bot_difficulty=payload.bot_difficulty,
        invite_token=secrets.token_urlsafe(32),
    )
    db.add(room)
    await db.flush()
    db.add(RoomParticipant(room_id=room.id, user_id=user.id, seat_index=0, ready=True))
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
    return RoomInviteResponse(
        id=room.id,
        name=room.name,
        game=game.name if game else "Game",
        players=players,
        max_players=room.max_players,
        status=room.status,
        invite_token=room.invite_token,
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


@router.post("/games/rooms/{room_id}/join", response_model=RoomResponse)
async def join_room(room_id: int, user: CurrentUser, db: DbSession) -> RoomResponse:
    room = await db.scalar(select(GameRoom).where(GameRoom.id == room_id).with_for_update())
    if room is None or room.status != "open":
        raise HTTPException(status_code=404, detail="Room not available")
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
async def get_room(room_id: int, user: CurrentUser, db: DbSession) -> RoomResponse:
    room = await db.get(GameRoom, room_id)
    if room is None or room.status not in {"open", "active"}:
        raise HTTPException(status_code=404, detail="Room not available")
    participant = await db.scalar(
        select(RoomParticipant.id).where(
            RoomParticipant.room_id == room_id, RoomParticipant.user_id == user.id
        )
    )
    if participant is None:
        raise HTTPException(status_code=403, detail="You are not a participant in this room")
    return await room_out(room, user.id, db)


@router.get("/games/rooms/{room_id}/participants", response_model=list[RoomParticipantResponse])
async def list_room_participants(
    room_id: int, user: CurrentUser, db: DbSession
) -> list[RoomParticipantResponse]:
    room = await db.get(GameRoom, room_id)
    if room is None:
        raise HTTPException(status_code=404, detail="Room not found")
    membership = await db.scalar(
        select(RoomParticipant.id).where(
            RoomParticipant.room_id == room_id, RoomParticipant.user_id == user.id
        )
    )
    if membership is None:
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
    if room.max_players > capacity or len(participants) > capacity:
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
    match = match_manager.create(
        room.id, user.id, payload.with_bot, payload.bot_difficulty, player_ids, player_names
    )
    room.status = "active"
    await create_persisted_match(
        db, match.id, room.id, "connect-four", user.id, match.snapshot(), seats
    )
    await db.commit()
    return match_response(match, user.id)


@router.get("/games/matches/{match_id}", response_model=MatchResponse)
async def get_match(match_id: str, user: CurrentUser) -> MatchResponse:
    match = match_manager.get(match_id)
    if match is None:
        match, _ = await hydrate_match(match_id)
    if match is None:
        raise HTTPException(status_code=404, detail="Match not found")
    if user.id not in match.player_ids:
        raise HTTPException(status_code=403, detail="You are not a player in this match")
    return match_response(match, user.id)


@router.post("/games/matches/{match_id}/moves", response_model=MatchResponse)
async def play_move(
    match_id: str, payload: MoveRequest, user: CurrentUser, db: DbSession
) -> MatchResponse:
    match = match_manager.get(match_id)
    if match is None:
        raise HTTPException(status_code=404, detail="Match not found")
    try:
        await match_manager.move(match, user.id, payload.column)
    except IllegalMove as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    persisted = await db.get(GameMatch, match.id)
    if persisted is not None:
        await record_state(db, persisted, user.id, {"column": payload.column}, match.snapshot())
    await grant_game_participation_reward(db, user.id, match.id)
    if match.state.winner is not None or match.state.draw:
        await grant_completed_game_rewards(db, match.player_ids, match.id, match.state.winner)
        match.reward_granted = match.state.winner is not None
        if persisted is not None:
            persisted.status = "completed"
        await db.commit()
    else:
        await db.commit()
    await realtime_bus.publish(
        match_channel(match.id),
        {
            "origin": get_settings().realtime_node_id,
            "payload": {"type": "state", "state": match.snapshot()},
        },
    )
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


@router.websocket("/games/matches/{match_id}/ws")
async def match_socket(websocket: WebSocket, match_id: str) -> None:
    match = match_manager.get(match_id)
    if match is None:
        match, _ = await hydrate_match(match_id)
    user = await websocket_user(websocket)
    if match is None or user is None or user.id not in match.player_ids:
        await websocket.close(code=1008)
        return
    await websocket.accept()
    match.sockets[websocket] = user.id
    relay_task = asyncio.create_task(relay_remote_events(websocket, match.id))
    await websocket.send_json({"type": "state", "state": match.snapshot(user.id)})
    try:
        while True:
            message = await websocket.receive_json()
            if message.get("type") == "play_again":
                try:
                    await match_manager.play_again(match, user.id)
                except IllegalMove as error:
                    await websocket.send_json({"type": "error", "detail": str(error)})
                else:
                    async with session_factory() as db:
                        persisted = await db.get(GameMatch, match.id)
                        if persisted is not None:
                            await record_state(db, persisted, user.id, {"action": "play_again"}, match.snapshot())
                            persisted.status = "active"
                        await db.commit()
                continue
            if message.get("type") != "move" or not isinstance(message.get("column"), int):
                await websocket.send_json(
                    {"type": "error", "detail": "Send a move with a numeric column"}
                )
                continue
            try:
                await match_manager.move(match, user.id, message["column"])
            except IllegalMove as error:
                await websocket.send_json({"type": "error", "detail": str(error)})
                continue
            async with session_factory() as db:
                persisted = await db.get(GameMatch, match.id)
                if persisted is not None:
                    await record_state(
                        db, persisted, user.id, {"column": message["column"]}, match.snapshot()
                    )
                await grant_game_participation_reward(db, user.id, match.id)
                if match.state.winner is not None or match.state.draw:
                    await grant_completed_game_rewards(
                        db, match.player_ids, match.id, match.state.winner
                    )
                await db.commit()
            await realtime_bus.publish(
                match_channel(match.id),
                {
                    "origin": get_settings().realtime_node_id,
                    "payload": {"type": "state", "state": match.snapshot()},
                },
            )
            if match.state.winner is not None or match.state.draw:
                match.reward_granted = match.state.winner is not None
    except WebSocketDisconnect:
        match.sockets.pop(websocket, None)
    finally:
        relay_task.cancel()


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
    match = universal_matches.create(
        room.id,
        user.id,
        game_type,
        min(room.max_players, game_capacity(game_type)),
        player_ids=player_ids,
        bot_players=bot_players,
        player_names=player_names,
    )
    room.status = "active"
    await create_persisted_match(db, match.id, room.id, game_type, user.id, match.state, seats)
    await db.commit()
    return universal_response(match, user.id)


@router.get("/games/sessions/{match_id}", response_model=GameSessionResponse)
async def get_game_session(match_id: str, user: CurrentUser) -> GameSessionResponse:
    match = universal_matches.get(match_id)
    if match is None:
        _, match = await hydrate_match(match_id)
    if match is None:
        raise HTTPException(status_code=404, detail="Game session not found")
    if user.id not in match.player_ids:
        raise HTTPException(status_code=403, detail="You are not a player in this match")
    return universal_response(match, user.id)


@router.post("/games/sessions/{match_id}/actions", response_model=GameSessionResponse)
async def game_session_action(
    match_id: str, payload: GameActionRequest, user: CurrentUser, db: DbSession
) -> GameSessionResponse:
    match = universal_matches.get(match_id)
    if match is None:
        _, match = await hydrate_match(match_id)
    if match is None:
        raise HTTPException(status_code=404, detail="Game session not found")
    try:
        await universal_matches.action(match, user.id, payload.action)
    except IllegalMove as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    persisted = await db.get(GameMatch, match.id)
    if persisted is not None:
        await record_state(db, persisted, user.id, payload.action, match.state)
        if payload.action.get("action") == "play_again":
            persisted.status = "active"
        elif match.state.get("winner") is not None or match.state.get("draw", False):
            persisted.status = "completed"
    await grant_game_participation_reward(db, user.id, match.id)
    if match.state.get("winner") is not None or match.state.get("draw", False):
        await grant_completed_game_rewards(
            db, match.player_ids, match.id, match.state.get("winner")
        )
        match.reward_granted = match.state.get("winner") is not None
    await db.commit()
    await realtime_bus.publish(
        match_channel(match.id),
        {
            "origin": get_settings().realtime_node_id,
            "payload": {"type": "refresh", "match_id": match.id},
        },
    )
    return universal_response(match, user.id)


@router.websocket("/games/sessions/{match_id}/ws")
async def game_session_socket(websocket: WebSocket, match_id: str) -> None:
    match = universal_matches.get(match_id)
    if match is None:
        _, match = await hydrate_match(match_id)
    user = await websocket_user(websocket)
    if match is None or user is None or user.id not in match.player_ids:
        await websocket.close(code=1008)
        return
    await websocket.accept()
    match.sockets[websocket] = user.id
    relay_task = asyncio.create_task(relay_remote_universal_events(websocket, match, user.id))
    await websocket.send_json({"type": "state", "match": match.snapshot(user.id)})
    try:
        while True:
            message = await websocket.receive_json()
            if message.get("type") != "action" or not isinstance(message.get("action"), dict):
                await websocket.send_json({"type": "error", "detail": "Send an action object"})
                continue
            try:
                await universal_matches.action(match, user.id, message["action"])
            except IllegalMove as error:
                await websocket.send_json({"type": "error", "detail": str(error)})
                continue
            # Drawing segments are deliberately ephemeral websocket events.
            # Persisting and rebroadcasting the entire growing canvas for every
            # pointer move overwhelms the connection and lets stale snapshots
            # resurrect erased pixels. The completed state is persisted by the
            # next meaningful action (finish, clear, or round transition).
            if match.game_type == "scribble" and message["action"].get("action") == "stroke_segment":
                await realtime_bus.publish(
                    match_channel(match.id),
                    {
                        "origin": get_settings().realtime_node_id,
                        "payload": {"type": "drawing_segment", "segment": match.state["strokes"][-1]},
                    },
                )
                continue
            # Broadcast updates the other players. Send the acting player's
            # authoritative snapshot directly as well so their own token
            # animation cannot be lost in websocket/realtime timing.
            await websocket.send_json({"type": "state", "match": match.snapshot(user.id)})
            async with session_factory() as db:
                persisted = await db.get(GameMatch, match.id)
                if persisted is not None:
                    await record_state(db, persisted, user.id, message["action"], match.state)
                    if message["action"].get("action") == "play_again":
                        persisted.status = "active"
                    elif match.state.get("winner") is not None or match.state.get("draw", False):
                        persisted.status = "completed"
                await grant_game_participation_reward(db, user.id, match.id)
                if match.state.get("winner") is not None or match.state.get("draw", False):
                    await grant_completed_game_rewards(
                        db, match.player_ids, match.id, match.state.get("winner")
                    )
                    match.reward_granted = match.state.get("winner") is not None
                await db.commit()
            await realtime_bus.publish(
                match_channel(match.id),
                {
                    "origin": get_settings().realtime_node_id,
                    "payload": {"type": "refresh", "match_id": match.id},
                },
            )
    except WebSocketDisconnect:
        match.sockets.pop(websocket, None)
    finally:
        relay_task.cancel()


@router.get("/games/winners", response_model=list[dict[str, object]])
async def list_winners(
    user: CurrentUser, db: DbSession, page: int = 1, limit: int = 10
) -> list[dict[str, object]]:
    del user
    page = max(page, 1)
    limit = min(max(limit, 1), 100)
    totals = (
        await db.execute(
            select(
                RewardLedger.user_id,
                User.name,
                User.avatar_url,
                func.sum(RewardLedger.xp).label("points"),
                func.count(RewardLedger.id).label("wins"),
                func.max(RewardLedger.created_at).label("latest_win"),
            )
            .join(User, User.id == RewardLedger.user_id)
            .where(RewardLedger.kind == "game_win", User.is_guest.is_(False))
            .group_by(RewardLedger.user_id, User.name, User.avatar_url)
            .order_by(func.sum(RewardLedger.xp).desc(), func.max(RewardLedger.created_at).desc(), User.name.asc())
            .offset((page - 1) * limit)
            .limit(limit)
        )
    ).all()
    result: list[dict[str, object]] = []
    for position, row in enumerate(totals, start=(page - 1) * limit + 1):
        latest = await db.scalar(
            select(RewardLedger)
            .where(RewardLedger.user_id == row.user_id, RewardLedger.kind == "game_win")
            .order_by(RewardLedger.created_at.desc())
            .limit(1)
        )
        # Older reward rows may not have a persisted match id. Never pass a
        # NULL identity to AsyncSession.get(), which emits a SQLAlchemy
        # warning and can become an error in a future release.
        game_name = latest.match_id if latest and latest.match_id else None
        match = await db.get(GameMatch, game_name) if game_name else None
        game_label = (match.game_type.replace("-", " ").title() if match else "Game")
        result.append(
            {
                "position": position,
                "name": row.name,
                "avatar_url": row.avatar_url,
                "points": int(row.points or 0),
                "match_points": int(latest.xp if latest else 0),
                "wins": int(row.wins or 0),
                "game": game_label,
                "created_at": row.latest_win,
            }
        )
    return result


def leaderboard_query(period: str):
    """Return members and the XP earned in the requested ranking window."""
    member_filter = User.is_guest.is_(False)
    if period == "all":
        return select(User, User.xp.label("ranking_xp")).where(member_filter)

    start = leaderboard_period_start(period)
    reward_totals = (
        select(
            RewardLedger.user_id,
            func.coalesce(func.sum(RewardLedger.xp), 0).label("reward_xp"),
        )
        .where(RewardLedger.created_at >= start)
        .group_by(RewardLedger.user_id)
        .subquery()
    )
    checkin_totals = (
        select(
            CheckIn.user_id,
            (func.count(CheckIn.id) * 25).label("checkin_xp"),
        )
        .where(CheckIn.created_at >= start, CheckIn.completed.is_(True))
        .group_by(CheckIn.user_id)
        .subquery()
    )
    challenge_totals = (
        select(
            ChallengeCompletion.user_id,
            func.coalesce(func.sum(ChallengeCompletion.xp_awarded), 0).label("challenge_xp"),
        )
        .where(ChallengeCompletion.created_at >= start)
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
    return AdminDashboardResponse(
        total_members=total_members or 0,
        pending_members=pending_members or 0,
        open_bug_reports=open_bug_reports or 0,
        pending_quotes=pending_quotes or 0,
        active_rooms=active_rooms or 0,
        total_quotes=total_quotes or 0,
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
    if payload.role is None and payload.is_approved is None:
        raise HTTPException(status_code=422, detail="Provide a role or approval change")
    if member.id == admin.id and payload.role not in {None, "admin", "super_admin"}:
        raise HTTPException(status_code=400, detail="You cannot remove your own admin access")
    if payload.role is not None:
        member.role = payload.role
    if payload.is_approved is not None:
        member.is_approved = payload.is_approved
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
