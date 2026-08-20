"""Add per-user email notification preferences."""

import sqlalchemy as sa
from alembic import op

revision = "20260816_0020"
down_revision = "20260816_0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "email_notifications_enabled",
            sa.Boolean(),
            server_default=sa.true(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "email_notifications_enabled")
