import json
import logging
from collections.abc import AsyncIterator
from typing import Any

from redis.asyncio import Redis

from app.config import get_settings

logger = logging.getLogger("safe_space_saturdays.games.realtime")


class RealtimeBus:
    def __init__(self) -> None:
        self._client: Redis | None = None

    def client(self) -> Redis:
        if self._client is None:
            self._client = Redis.from_url(get_settings().redis_url, decode_responses=True)
        return self._client

    async def publish(self, channel: str, message: dict[str, Any]) -> None:
        try:
            await self.client().publish(channel, json.dumps(message))
        except Exception:
            # A single-container/local run remains usable when Redis is unavailable.
            logger.warning("realtime_publish_failed channel=%s", channel, exc_info=True)
            return

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def subscribe(self, channel: str) -> AsyncIterator[dict[str, Any]]:
        pubsub = self.client().pubsub()
        try:
            await pubsub.subscribe(channel)
            async for message in pubsub.listen():
                if message.get("type") != "message":
                    continue
                try:
                    yield json.loads(message["data"])
                except (TypeError, json.JSONDecodeError):
                    continue
        except Exception:
            logger.warning("realtime_subscribe_failed channel=%s", channel, exc_info=True)
            return
        finally:
            try:
                await pubsub.unsubscribe(channel)
                await pubsub.close()
            except Exception:
                logger.warning(
                    "realtime_subscription_close_failed channel=%s", channel, exc_info=True
                )


realtime_bus = RealtimeBus()
