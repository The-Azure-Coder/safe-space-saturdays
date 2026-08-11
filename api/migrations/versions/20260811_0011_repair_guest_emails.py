"""Repair legacy guest email addresses rejected by EmailStr."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260811_0011"
down_revision: str | Sequence[str] | None = "20260810_0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            UPDATE users
            SET email = 'guest-' || id::text || '@guests.safespacesaturdays.app'
            WHERE is_guest IS TRUE AND email LIKE '%@guest.invalid'
            """
        )
    )


def downgrade() -> None:
    # Restoring invalid addresses would break authenticated API responses again.
    pass
