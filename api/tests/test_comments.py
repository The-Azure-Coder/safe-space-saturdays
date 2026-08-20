from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

import app.routes.api as api_routes
from app.routes.api import edit_comment, edit_community_post
from app.schemas import CommentUpdateRequest, PostUpdateRequest


class FakeCommentDb:
    def __init__(self, comment: SimpleNamespace) -> None:
        self.comment = comment
        self.committed = False

    async def get(self, model: object, comment_id: int) -> SimpleNamespace | None:
        return self.comment if self.comment.id == comment_id else None

    async def commit(self) -> None:
        self.committed = True

    async def refresh(self, comment: SimpleNamespace) -> None:
        return None


class FakePostDb(FakeCommentDb):
    pass


def make_comment() -> SimpleNamespace:
    return SimpleNamespace(
        id=7,
        post_id=3,
        user_id=11,
        text="Original reply",
        created_at=datetime.now(UTC),
    )


@pytest.mark.asyncio
async def test_member_can_edit_their_own_comment() -> None:
    comment = make_comment()
    db = FakeCommentDb(comment)
    user = SimpleNamespace(id=11, name="Member", avatar_url=None)

    response = await edit_comment(7, CommentUpdateRequest(text=" Updated reply "), user, db)  # type: ignore[arg-type]

    assert response.text == "Updated reply"
    assert comment.text == "Updated reply"
    assert db.committed is True


@pytest.mark.asyncio
async def test_member_cannot_edit_another_members_comment() -> None:
    db = FakeCommentDb(make_comment())
    user = SimpleNamespace(id=22, name="Other member", avatar_url=None)

    with pytest.raises(HTTPException) as error:
        await edit_comment(7, CommentUpdateRequest(text="Tampered reply"), user, db)  # type: ignore[arg-type]

    assert error.value.status_code == 403
    assert db.committed is False


def test_comment_text_cannot_be_blank_after_trimming() -> None:
    with pytest.raises(ValidationError):
        CommentUpdateRequest(text="   ")


def make_post() -> SimpleNamespace:
    return SimpleNamespace(
        id=3,
        user_id=11,
        text="Original post",
        is_hidden=False,
    )


@pytest.mark.asyncio
async def test_member_can_edit_their_own_post(monkeypatch: pytest.MonkeyPatch) -> None:
    post = make_post()
    db = FakePostDb(post)
    user = SimpleNamespace(id=11, name="Member", avatar_url=None)

    async def fake_post_out(updated_post: SimpleNamespace, user_id: int, database: object) -> SimpleNamespace:
        del user_id, database
        return SimpleNamespace(text=updated_post.text)

    monkeypatch.setattr(api_routes, "post_out", fake_post_out)
    response = await edit_community_post(3, PostUpdateRequest(text=" Updated post "), user, db)  # type: ignore[arg-type]

    assert response.text == "Updated post"
    assert post.text == "Updated post"
    assert db.committed is True


@pytest.mark.asyncio
async def test_member_cannot_edit_another_members_post() -> None:
    db = FakePostDb(make_post())
    user = SimpleNamespace(id=22, name="Other member", avatar_url=None)

    with pytest.raises(HTTPException) as error:
        await edit_community_post(3, PostUpdateRequest(text="Tampered post"), user, db)  # type: ignore[arg-type]

    assert error.value.status_code == 403
