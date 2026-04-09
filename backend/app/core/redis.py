"""Redis connection pool singleton."""

import redis.asyncio as aioredis
from app.core.config import get_settings

settings = get_settings()

redis_pool = aioredis.from_url(
    settings.redis_url,
    decode_responses=True,
    max_connections=50,
)


async def get_redis() -> aioredis.Redis:
    return redis_pool
