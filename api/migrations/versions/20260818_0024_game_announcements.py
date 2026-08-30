"""Publish announcements for the new games."""

import sqlalchemy as sa
from alembic import op

revision = "20260818_0024"
down_revision = "20260818_0023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(sa.text("""
        INSERT INTO announcements (title, body, image_url, cta_label, cta_path, is_published, author_id)
        SELECT 'ABC Fast or Slow is here',
               'Spin the letter wheel, choose your pace, and race to find creative answers with friends.',
               '/assets/game-abc-fast-slow.png', 'Play ABC Fast or Slow', '/games', true, id
        FROM users WHERE role IN ('admin', 'super_admin') ORDER BY id LIMIT 1
    """))
    op.execute(sa.text("""
        INSERT INTO announcements (title, body, image_url, cta_label, cta_path, is_published, author_id)
        SELECT 'Checkers has arrived',
               'Settle in for a classic two-player game of thoughtful moves, clever jumps, and friendly competition.',
               '/assets/game-checkers.png', 'Play Checkers', '/games', true, id
        FROM users WHERE role IN ('admin', 'super_admin') ORDER BY id LIMIT 1
    """))


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM announcements WHERE title IN ('ABC Fast or Slow is here', 'Checkers has arrived')"))
