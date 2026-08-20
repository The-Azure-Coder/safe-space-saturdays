"""Backfill the recent rewards that were missed before game XP reconciliation."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260814_0015"
down_revision: str | None = "20260814_0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Keep the leaderboard's day/week filters correct by writing these as
    # ledger entries with the migration timestamp. The count guard makes this
    # safe if one or both matches were already recorded by the repaired flow.
    op.execute(
        sa.text(
            """
            INSERT INTO reward_ledger (user_id, match_id, kind, xp, idempotency_key)
            SELECT target.id, NULL, 'game_win', 10,
                   'manual-game-win:tyrese@gmail.com:' || series.number
            FROM users AS target
            CROSS JOIN LATERAL generate_series(
                1,
                GREATEST(
                    0,
                    2 - (
                        SELECT COUNT(*)
                        FROM reward_ledger AS existing
                        WHERE existing.user_id = target.id
                          AND existing.kind = 'game_win'
                          AND existing.created_at >= NOW() - INTERVAL '1 day'
                    )
                )
            ) AS series(number)
            WHERE LOWER(target.email) = 'tyrese@gmail.com'
              AND NOT EXISTS (
                  SELECT 1
                  FROM reward_ledger AS duplicate
                  WHERE duplicate.idempotency_key =
                        'manual-game-win:tyrese@gmail.com:' || series.number
              )
            """
        )
    )
    op.execute(
        sa.text(
            """
            INSERT INTO reward_ledger (user_id, match_id, kind, xp, idempotency_key)
            SELECT target.id, NULL, 'game_participation', 5,
                   'manual-game-participation:tyrese@gmail.com:' || series.number
            FROM users AS target
            CROSS JOIN LATERAL generate_series(
                1,
                GREATEST(
                    0,
                    2 - (
                        SELECT COUNT(*)
                        FROM reward_ledger AS existing
                        WHERE existing.user_id = target.id
                          AND existing.kind = 'game_participation'
                          AND existing.created_at >= NOW() - INTERVAL '1 day'
                    )
                )
            ) AS series(number)
            WHERE LOWER(target.email) = 'tyrese@gmail.com'
              AND NOT EXISTS (
                  SELECT 1
                  FROM reward_ledger AS duplicate
                  WHERE duplicate.idempotency_key =
                        'manual-game-participation:tyrese@gmail.com:' || series.number
              )
            """
        )
    )
    op.execute(
        sa.text(
            """
            INSERT INTO reward_ledger (user_id, match_id, kind, xp, idempotency_key)
            SELECT target.id, NULL, 'community_post', 5,
                   'manual-community-post:francistattyanna@gmail.com'
            FROM users AS target
            WHERE LOWER(target.email) = 'francistattyanna@gmail.com'
              AND NOT EXISTS (
                  SELECT 1
                  FROM reward_ledger AS duplicate
                  WHERE duplicate.idempotency_key =
                        'manual-community-post:francistattyanna@gmail.com'
              )
            """
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            """
            DELETE FROM reward_ledger
            WHERE idempotency_key IN (
                'manual-game-win:tyrese@gmail.com:1',
                'manual-game-win:tyrese@gmail.com:2',
                'manual-game-participation:tyrese@gmail.com:1',
                'manual-game-participation:tyrese@gmail.com:2',
                'manual-community-post:francistattyanna@gmail.com'
            )
            """
        )
    )
