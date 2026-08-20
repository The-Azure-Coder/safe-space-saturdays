from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.routes.api import edit_comment
from app.schemas import CommentUpdateRequest


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
