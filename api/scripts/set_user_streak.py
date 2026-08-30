"""Set one user's persisted check-in streak using the configured database."""

from __future__ import annotations

import argparse
import asyncio

from sqlalchemy import func, select

from app.db import engine
from app.models import User


async def update_streak(name: str, streak: int, apply: bool) -> None:
    from sqlalchemy.ext.asyncio import async_sessionmaker

    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with sessions() as session:
        users = (
            await session.scalars(select(User).where(func.lower(User.name) == name.casefold()))
        ).all()
        if len(users) != 1:
            names = ", ".join(f"{user.id}:{user.name}" for user in users) or "no matches"
            raise SystemExit(f"Expected exactly one user named {name!r}; found {names}")

        user = users[0]
        print(f"User {user.id} ({user.name}): streak {user.streak} -> {streak}")
        if not apply:
            print("Dry run only. Re-run with --apply to commit this change.")
            return

        user.streak = streak
        await session.commit()
        await session.refresh(user)
        if user.streak != streak:
            raise RuntimeError(f"Verification failed: database returned streak {user.streak}")
        print(f"Verified persisted streak: {user.streak}")

    await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", default="Tushaii")
    parser.add_argument("--streak", type=int, default=9)
    parser.add_argument("--apply", action="store_true", help="commit the database update")
    args = parser.parse_args()
    if args.streak < 0:
        parser.error("--streak must be zero or greater")
    asyncio.run(update_streak(args.name, args.streak, args.apply))


if __name__ == "__main__":
    main()
