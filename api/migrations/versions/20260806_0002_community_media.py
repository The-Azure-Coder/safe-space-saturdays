"""Add optional images to community posts."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260806_0002"
down_revision: str | Sequence[str] | None = "20260805_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("posts", sa.Column("image_url", sa.String(length=500), nullable=True))
    op.drop_constraint("uq_post_reaction", "post_reactions", type_="unique")
    op.execute("UPDATE post_reactions SET kind = 'love' WHERE kind = 'support'")
    op.create_check_constraint(
        "ck_post_reaction_kind", "post_reactions", "kind IN ('like', 'dislike', 'love')"
    )


def downgrade() -> None:
    op.drop_constraint("ck_post_reaction_kind", "post_reactions", type_="check")
    op.create_unique_constraint(
        "uq_post_reaction", "post_reactions", ["post_id", "user_id", "kind"]
    )
    op.drop_column("posts", "image_url")
