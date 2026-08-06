import asyncio
from collections import Counter
from pathlib import Path
from typing import Annotated
from uuid import uuid4

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    Response,
    UploadFile,
    status,
)
from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import get_session
from app.models import (
    BugReport,
    CheckIn,
    Comment,
    Game,
    GameRoom,
    GameWinner,
    Post,
    PostReaction,
    Quote,
    RoomParticipant,
    SavedQuote,
    Session,
    User,
)
from app.schemas import (
    AdminPasswordResetRequest,
    AdminQuoteCreateRequest,
    AdminQuoteUpdateRequest,
    AdminUserUpdateRequest,
    AuthResponse,
    BugReportCreateRequest,
    BugReportResponse,
    BugReportUpdateRequest,
    CheckInRequest,
    CheckInResponse,
    CommentCreateRequest,
    CommentResponse,
    DashboardResponse,
    GameResponse,
    LeaderboardEntry,
    LoginRequest,
    PostCreateRequest,
    PostResponse,
    ProfileUpdateRequest,
    QuoteResponse,
    ReactionRequest,
    RegisterRequest,
    RoomCreateRequest,
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


def user_response(user: User) -> UserResponse:
    return UserResponse.model_validate(user)


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


async def set_session(
    response: Response, db: AsyncSession, user: User, remember_me: bool = True
) -> None:
    token, token_hash = new_session_token()
    db.add(Session(user_id=user.id, token_hash=token_hash, expires_at=session_expiry(remember_me)))
    await db.commit()
    response.set_cookie(
        get_settings().session_cookie_name,
        token,
        httponly=True,
        secure=get_settings().cookie_secure,
        samesite="lax",
        max_age=60 * 60 * 24 * (get_settings().session_ttl_days if remember_me else 1),
    )


@router.post("/auth/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, response: Response, db: DbSession) -> AuthResponse:
    email = payload.email.lower()
    existing = await db.scalar(select(User).where(User.email == email))
    if existing:
        raise HTTPException(status_code=409, detail="An account with this email already exists")
    user = User(
        name=payload.name.strip(),
        email=email,
        password_hash=hash_password(payload.password),
        level=1,
    )
    db.add(user)
    await db.flush()
    await set_session(response, db, user)
    return AuthResponse(user=user_response(user))


@router.post("/auth/login", response_model=AuthResponse)
async def login(payload: LoginRequest, response: Response, db: DbSession) -> AuthResponse:
    user = await db.scalar(select(User).where(User.email == payload.email.lower()))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    await set_session(response, db, user, payload.remember_me)
    return AuthResponse(user=user_response(user))


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(request: Request, response: Response, db: DbSession) -> None:
    token = request.cookies.get(get_settings().session_cookie_name)
    if token:
        import hashlib

        await db.execute(
            delete(Session).where(Session.token_hash == hashlib.sha256(token.encode()).hexdigest())
        )
        await db.commit()
    response.delete_cookie(get_settings().session_cookie_name)


@router.get("/auth/me", response_model=UserResponse)
async def me(user: CurrentUser) -> UserResponse:
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
    rank = (await db.scalar(select(func.count(User.id)).where(User.xp > user.xp)) or 0) + 1
    quote_response = None if quote is None else QuoteResponse.model_validate(quote)
    checkin_response = None if latest is None else CheckInResponse.model_validate(latest)
    return DashboardResponse(
        user=user_response(user),
        featured_quote=quote_response,
        latest_check_in=checkin_response,
        rank=rank,
        level_progress=min(100, (user.xp % 250) * 100 // 250),
    )


@router.post("/check-ins", response_model=CheckInResponse, status_code=status.HTTP_201_CREATED)
async def create_check_in(
    payload: CheckInRequest, user: CurrentUser, db: DbSession
) -> CheckInResponse:
    checkin = CheckIn(user_id=user.id, **payload.model_dump())
    db.add(checkin)
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
    query = select(Quote).order_by(Quote.is_featured.desc(), Quote.id)
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
    if quote is None:
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
                text=comment.text,
                created_at=comment.created_at,
            )
        )
    counts = Counter(reactions)
    return PostResponse(
        id=post.id,
        author=author.name if author else "Member",
        initials=(author.name[0].upper() if author else "M"),
        text=post.text,
        image_url=post.image_url,
        created_at=post.created_at,
        likes=counts["like"],
        dislikes=counts["dislike"],
        loves=counts["love"],
        my_reaction=my_reaction,
        comments=comment_responses,
        mine=post.user_id == user_id,
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
    content = await image.read(settings.max_upload_bytes + 1)
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(status_code=413, detail="Image must be 5 MB or smaller")
    signature = image_format[1]
    if not content.startswith(signature) or (
        image_format[0] == "webp" and content[8:12] != b"WEBP"
    ):
        raise HTTPException(status_code=415, detail="The uploaded file is not a valid image")
    filename = f"{uuid4().hex}.{image_format[0]}"
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
    joined = (
        await db.scalar(
            select(RoomParticipant.id).where(
                RoomParticipant.room_id == room.id, RoomParticipant.user_id == user_id
            )
        )
        is not None
    )
    return RoomResponse(
        id=room.id,
        name=room.name,
        game=game.name if game else "Game",
        players=participants,
        max_players=room.max_players,
        status=room.status,
        joined=joined,
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
            .where(GameRoom.status == "open")
            .order_by(GameRoom.created_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        )
    ).all()
    return [await room_out(room, user.id, db) for room in rooms]


@router.post("/games/rooms", response_model=RoomResponse, status_code=status.HTTP_201_CREATED)
async def create_room(payload: RoomCreateRequest, user: CurrentUser, db: DbSession) -> RoomResponse:
    if await db.get(Game, payload.game_id) is None:
        raise HTTPException(status_code=404, detail="Game not found")
    room = GameRoom(
        game_id=payload.game_id,
        host_id=user.id,
        name=payload.name.strip(),
        max_players=payload.max_players,
    )
    db.add(room)
    await db.flush()
    db.add(RoomParticipant(room_id=room.id, user_id=user.id))
    await db.commit()
    return await room_out(room, user.id, db)


@router.post("/games/rooms/{room_id}/join", response_model=RoomResponse)
async def join_room(room_id: int, user: CurrentUser, db: DbSession) -> RoomResponse:
    room = await db.get(GameRoom, room_id)
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
        db.add(RoomParticipant(room_id=room_id, user_id=user.id))
        await db.commit()
    return await room_out(room, user.id, db)


@router.get("/games/winners", response_model=list[dict[str, object]])
async def list_winners(
    user: CurrentUser, db: DbSession, page: int = 1, limit: int = 10
) -> list[dict[str, object]]:
    page = max(page, 1)
    limit = min(max(limit, 1), 100)
    winners = (
        await db.scalars(
            select(GameWinner)
            .order_by(GameWinner.created_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        )
    ).all()
    result: list[dict[str, object]] = []
    for winner in winners:
        member = await db.get(User, winner.user_id)
        game = await db.get(Game, winner.game_id)
        result.append(
            {
                "id": winner.id,
                "name": member.name if member else "Member",
                "game": game.name if game else "Game",
                "result": winner.result,
                "created_at": winner.created_at,
            }
        )
    return result


@router.get("/leaderboard", response_model=list[LeaderboardEntry])
async def leaderboard(
    user: CurrentUser, db: DbSession, period: str = "week", page: int = 1, limit: int = 10
) -> list[LeaderboardEntry]:
    if period not in {"week", "month", "all"}:
        raise HTTPException(status_code=422, detail="Invalid leaderboard period")
    page = max(page, 1)
    limit = min(max(limit, 1), 100)
    users = (
        await db.scalars(
            select(User)
            .order_by(User.xp.desc(), User.created_at.asc())
            .offset((page - 1) * limit)
            .limit(limit)
        )
    ).all()
    return [
        LeaderboardEntry(rank=(page - 1) * limit + index, user=user_response(member))
        for index, member in enumerate(users, start=1)
    ]


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
    member = await db.get(User, user_id)
    if member is None:
        raise HTTPException(status_code=404, detail="User not found")
    if member.id == admin.id and payload.role != "admin":
        raise HTTPException(status_code=400, detail="You cannot remove your own admin access")
    member.role = payload.role
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
    del admin
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
    del admin
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
