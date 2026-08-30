"""Persist each member's highest check-in streak.

This migration remains part of the Alembic chain because some environments
already applied revision 20260830_0029. The application no longer exposes this
field, but keeping the revision makes upgrades and rollbacks deterministic.
"""

from alembic import op
import sqlalchemy as sa


revision = "20260830_0029"
down_revision = "20260830_0028"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("highest_streak", sa.Integer(), nullable=False, server_default="0"))
    op.execute(sa.text("UPDATE users SET highest_streak = streak"))


def downgrade() -> None:
    op.drop_column("users", "highest_streak")
