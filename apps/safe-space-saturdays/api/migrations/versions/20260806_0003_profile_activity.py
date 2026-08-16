"""Add persisted profile avatars for account activity."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260806_0003"
down_revision: str | Sequence[str] | None = "20260806_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("avatar_url", sa.String(length=500), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "avatar_url")
