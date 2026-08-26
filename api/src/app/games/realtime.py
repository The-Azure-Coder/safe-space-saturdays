import json
import logging
import time
from collections.abc import AsyncIterator
from typing import Any

from redis.asyncio import Redis
from redis.exceptions import ConnectionError as RedisConnectionError

from app.config import get_settings

logger = logging.getLogger("safe_space_saturdays.games.realtime")


class RealtimeBus:
    def __init__(self) -> None:
        self._client: Redis | None = None
        self._unavailable_until = 0.0

    def client(self) -> Redis:
        if self._client is None:
            self._client = Redis.from_url(get_settings().redis_url, decode_responses=True)
        return self._client

    async def publish(self, channel: str, message: dict[str, Any]) -> None:
        if time.monotonic() < self._unavailable_until:
            return
        try:
            await self.client().publish(channel, json.dumps(message))
        except RedisConnectionError:
            # A single-container/local run remains usable when Redis is unavailable.
            self._unavailable_until = time.monotonic() + 10
            logger.warning("realtime_publish_failed channel=%s redis_unavailable=true", channel)
            return

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def subscribe(self, channel: str) -> AsyncIterator[dict[str, Any]]:
        if time.monotonic() < self._unavailable_until:
            return
        pubsub = self.client().pubsub()
        subscribed = False
        try:
            await pubsub.subscribe(channel)
            subscribed = True
            async for message in pubsub.listen():
                if message.get("type") != "message":
                    continue
                try:
                    yield json.loads(message["data"])
                except (TypeError, json.JSONDecodeError):
                    continue
        except RedisConnectionError:
            self._unavailable_until = time.monotonic() + 10
            logger.warning("realtime_subscribe_failed channel=%s redis_unavailable=true", channel)
            return
        finally:
            if subscribed:
                try:
                    await pubsub.unsubscribe(channel)
                except RedisConnectionError:
                    pass
            await pubsub.close()


realtime_bus = RealtimeBus()
