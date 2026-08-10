from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    email: EmailStr
    avatar_url: str | None = None
    is_online: bool = False
    role: str
    is_approved: bool
    xp: int
    streak: int
    level: int


class RegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)
    confirm_password: str = Field(min_length=10, max_length=128)

    @model_validator(mode="after")
    def passwords_match(self) -> "RegisterRequest":
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match")
        return self


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)
    remember_me: bool = True


class AuthResponse(BaseModel):
    user: UserResponse
    pending_approval: bool = False
    message: str | None = None


class BugReportCreateRequest(BaseModel):
    title: str = Field(min_length=3, max_length=160)
    description: str = Field(min_length=10, max_length=5000)
    severity: Literal["low", "normal", "high", "critical"] = "normal"
    page_url: str | None = Field(default=None, max_length=500)


class BugReportUpdateRequest(BaseModel):
    status: Literal["open", "in_progress", "resolved", "closed"]
    admin_note: str | None = Field(default=None, max_length=5000)


class BugReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int | None
    reporter_name: str
    reporter_email: EmailStr
    title: str
    description: str
    severity: str
    status: str
    page_url: str | None
    admin_note: str | None
    created_at: datetime
    updated_at: datetime


class AdminUserUpdateRequest(BaseModel):
    role: Literal["member", "moderator", "manager", "admin", "super_admin"] | None = None
    is_approved: bool | None = None


class AdminPasswordResetRequest(BaseModel):
    password: str = Field(min_length=10, max_length=128)


class AdminQuoteCreateRequest(BaseModel):
    text: str = Field(min_length=3, max_length=2000)
    author: str = Field(default="Safe Space Saturdays", min_length=2, max_length=120)
    category: Literal["Encouragement", "Rest", "Growth", "Connection"]
    is_featured: bool = False
    approval_status: Literal["pending", "approved", "rejected"] = "approved"


class AdminQuoteUpdateRequest(AdminQuoteCreateRequest):
    pass


class QuoteSubmissionRequest(BaseModel):
    text: str = Field(min_length=3, max_length=2000)
    author: str = Field(default="A Safe Space member", min_length=2, max_length=120)
    category: Literal["Encouragement", "Rest", "Growth", "Connection"]


class ProfileUpdateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=10, max_length=128)
    confirm_password: str = Field(min_length=10, max_length=128)

    @model_validator(mode="after")
    def passwords_match(self) -> "ChangePasswordRequest":
        if self.new_password != self.confirm_password:
            raise ValueError("Passwords do not match")
        return self


class QuoteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    text: str
    author: str
    category: str
    is_featured: bool
    saved: bool = False
    approval_status: Literal["pending", "approved", "rejected"] = "approved"
    submitted_by_user_id: int | None = None


class CheckInRequest(BaseModel):
    mood: str = Field(min_length=2, max_length=30)
    needs: list[str] = Field(default_factory=list, max_length=10)
    energy: int = Field(ge=1, le=5)
    stress: int = Field(ge=1, le=5)
    thoughts: str | None = Field(default=None, max_length=5000)
    gratitude: str | None = Field(default=None, max_length=1000)
    completed: bool = True


class CheckInResponse(CheckInRequest):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime


class PostResponse(BaseModel):
    id: int
    author: str
    initials: str
    avatar_url: str | None = None
    is_online: bool = False
    text: str
    image_url: str | None
    created_at: datetime
    likes: int
    dislikes: int
    loves: int
    my_reaction: Literal["like", "dislike", "love"] | None = None
    comments: list["CommentResponse"] = Field(default_factory=list)
    mine: bool
    post_type: Literal["original", "shared_quote"] = "original"
    shared_quote_id: int | None = None


class PostCreateRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)


class ReactionRequest(BaseModel):
    kind: Literal["like", "dislike", "love"]


class CommentCreateRequest(BaseModel):
    text: str = Field(min_length=1, max_length=1000)


class CommentResponse(BaseModel):
    id: int
    post_id: int
    author: str
    initials: str
    avatar_url: str | None = None
    is_online: bool = False
    text: str
    created_at: datetime


class GameResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    players: str
    icon: str
    color: str
    is_featured: bool


class RoomResponse(BaseModel):
    id: int
    name: str
    game: str
    players: int
    max_players: int
    status: str
    joined: bool
    is_host: bool = False
    match_id: str | None = None
    ready: bool = False
    fill_with_bots: bool = True
    invite_token: str | None = None


class RoomInviteResponse(BaseModel):
    id: int
    name: str
    game: str
    players: int
    max_players: int
    status: str
    invite_token: str


class RoomParticipantResponse(BaseModel):
    user_id: int
    name: str
    avatar_url: str | None
    seat_index: int | None
    ready: bool
    is_host: bool


class RoomCreateRequest(BaseModel):
    game_id: int
    name: str = Field(min_length=2, max_length=100)
    max_players: int = Field(default=4, ge=2, le=8)
    fill_with_bots: bool = True
    bot_difficulty: Literal["friendly", "thoughtful"] = "friendly"


class RoomGameChangeRequest(BaseModel):
    game_id: int


class GuestRoomJoinRequest(BaseModel):
    name: str = Field(min_length=2, max_length=80)


class RoomCleanupResponse(BaseModel):
    deleted: int


class MatchCreateRequest(BaseModel):
    room_id: int
    with_bot: bool = True
    bot_difficulty: Literal["friendly", "thoughtful"] = "friendly"


class MatchResponse(BaseModel):
    match_id: str
    room_id: int
    game: str
    board: list[list[int]]
    current_player: Literal[1, 2]
    winner: Literal[1, 2] | None
    draw: bool
    move_count: int
    last_move: tuple[int, int] | None = None
    winning_cells: list[tuple[int, int]] = Field(default_factory=list)
    player: Literal[1, 2] | None = None
    players: list[dict[str, object]] = Field(default_factory=list)


class MoveRequest(BaseModel):
    column: int = Field(ge=0, le=6)


class GameSessionCreateRequest(BaseModel):
    room_id: int
    fill_with_bots: bool = True


class GameActionRequest(BaseModel):
    action: dict[str, object] = Field(default_factory=dict)


class GameSessionResponse(BaseModel):
    match_id: str
    room_id: int
    game: str
    state: dict[str, object]


class LeaderboardEntry(BaseModel):
    rank: int
    user: UserResponse


class DashboardResponse(BaseModel):
    user: UserResponse
    featured_quote: QuoteResponse | None
    latest_check_in: CheckInResponse | None
    rank: int
    level_progress: int
