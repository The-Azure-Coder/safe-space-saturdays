"""Add public community applications and one-time invite state."""

import sqlalchemy as sa
from alembic import op

revision = "20260816_0019"
down_revision = "20260816_0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "community_applications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("phone", sa.String(length=40), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="pending", nullable=False),
        sa.Column("admin_note", sa.Text(), nullable=True),
        sa.Column("reviewed_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("invite_token_hash", sa.String(length=128), nullable=True),
        sa.Column("invite_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("invite_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("email_sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_community_applications_status_created", "community_applications", ["status", "created_at"])
    op.create_index("ix_community_applications_email", "community_applications", ["email"])
    op.create_index("ix_community_applications_invite_token_hash", "community_applications", ["invite_token_hash"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_community_applications_invite_token_hash", table_name="community_applications")
    op.drop_index("ix_community_applications_email", table_name="community_applications")
    op.drop_index("ix_community_applications_status_created", table_name="community_applications")
    op.drop_table("community_applications")
