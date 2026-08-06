from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    email: EmailStr
    role: str
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


class ProfileUpdateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)


class QuoteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    text: str
    author: str
    category: str
    is_featured: bool
    saved: bool = False


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
    text: str
    image_url: str | None
    created_at: datetime
    likes: int
    dislikes: int
    loves: int
    my_reaction: Literal["like", "dislike", "love"] | None = None
    mine: bool


class PostCreateRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)


class ReactionRequest(BaseModel):
    kind: Literal["like", "dislike", "love"]


class CommentCreateRequest(BaseModel):
    text: str = Field(min_length=1, max_length=1000)


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


class RoomCreateRequest(BaseModel):
    game_id: int
    name: str = Field(min_length=2, max_length=100)
    max_players: int = Field(default=4, ge=2, le=8)


class LeaderboardEntry(BaseModel):
    rank: int
    user: UserResponse


class DashboardResponse(BaseModel):
    user: UserResponse
    featured_quote: QuoteResponse | None
    latest_check_in: CheckInResponse | None
    rank: int
    level_progress: int
