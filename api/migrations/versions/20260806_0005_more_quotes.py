"""Add an expanded set of original community quotes."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260806_0005"
down_revision: str | Sequence[str] | None = "20260806_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    quotes = sa.table(
        "quotes",
        sa.column("text", sa.Text()),
        sa.column("author", sa.String()),
        sa.column("category", sa.String()),
        sa.column("is_featured", sa.Boolean()),
    )
    op.bulk_insert(
        quotes,
        [
            {"text": "You can take the next step without seeing the whole path.", "author": "Safe Space Saturdays", "category": "Encouragement", "is_featured": False},
            {"text": "Rest is not falling behind; it is how you return to yourself.", "author": "Safe Space Saturdays", "category": "Rest", "is_featured": False},
            {"text": "Small, steady choices become a life that feels more like your own.", "author": "Safe Space Saturdays", "category": "Growth", "is_featured": False},
            {"text": "Being heard can be the beginning of feeling held.", "author": "Safe Space Saturdays", "category": "Connection", "is_featured": False},
            {"text": "You are allowed to begin again with gentleness.", "author": "Safe Space Saturdays", "category": "Encouragement", "is_featured": False},
            {"text": "A quiet day can still be a meaningful day.", "author": "Safe Space Saturdays", "category": "Rest", "is_featured": False},
            {"text": "Progress is allowed to look like patience.", "author": "Safe Space Saturdays", "category": "Growth", "is_featured": False},
            {"text": "There is room here for your honest self.", "author": "Safe Space Saturdays", "category": "Connection", "is_featured": False},
        ],
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            "DELETE FROM quotes WHERE author = :author AND text IN (:q1, :q2, :q3, :q4, :q5, :q6, :q7, :q8)"
        ).bindparams(
            author="Safe Space Saturdays",
            q1="You can take the next step without seeing the whole path.",
            q2="Rest is not falling behind; it is how you return to yourself.",
            q3="Small, steady choices become a life that feels more like your own.",
            q4="Being heard can be the beginning of feeling held.",
            q5="You are allowed to begin again with gentleness.",
            q6="A quiet day can still be a meaningful day.",
            q7="Progress is allowed to look like patience.",
            q8="There is room here for your honest self.",
        )
    )
