from __future__ import annotations

import time

from rate_limit.error import RateLimitResult
from rate_limit.observability import BucketSnapshot
from rate_limit.policy import Limit
from rate_limit.store.base import RateLimitStore

try:
    import redis.asyncio as redis
except ImportError:  # pragma: no cover
    redis = None


LUA_TOKEN_BUCKET = """
-- Redis key for one bucket
local key = KEYS[1]

-- Parameters passed from Python
local now = tonumber(ARGV[1])
local capacity = tonumber(ARGV[2])
local refill_rate = tonumber(ARGV[3])
local cost = tonumber(ARGV[4]) -- tokens per request
local ttl = tonumber(ARGV[5])

-- Load existing bucket state
local data = redis.call("HMGET", key, "tokens", "last_ts")
local tokens = tonumber(data[1])
local last_ts = tonumber(data[2])

-- Initialize if missing
if tokens == nil or last_ts == nil then
    tokens = capacity
    last_ts = now
end

-- Refill logic
local elapsed = now - last_ts
if elapsed < 0 then elapsed = 0 end

tokens = math.min(capacity, tokens + elapsed * refill_rate)
last_ts = now

-- Decide allow vs reject
local allowed = 0
local remaining = math.floor(tokens)
local retry_after = 0

-- Prepare result variables.
-- Enough tokens -> allow and consume.
if tokens >= cost then
    allowed = 1
    tokens = tokens - cost
    remaining = math.floor(tokens)

-- Not enough tokens -> compute how long until enough tokens refill.
else
    local needed = cost - tokens
    if refill_rate > 0 then
        retry_after = math.ceil(needed / refill_rate)
    else
        retry_after = ttl
    end
end

-- Persist state
redis.call("HMSET", key, "tokens", tokens, "last_ts", last_ts)
redis.call("EXPIRE", key, ttl)

return { allowed, remaining, retry_after }
"""


class RedisStore(RateLimitStore):
    """
    Redis-backed token bucket store.
    Safe for multi-instance deployments.

    Each bucket will be stored as:
      Redis hash:
        tokens
        last_ts
      With a TTL for eviction

      Key: rate:scope:user:123:cost:llm
      Value:
        tokens  -> 5.18
        last_ts -> 1723769200
    """

    def __init__(
        self,
        client: redis.Redis,
        *,
        ttl_seconds: int = 3600,
        key_prefix: str = "ratelimit:",
    ) -> None:
        if redis is None:
            raise RuntimeError("redis package is not installed")

        self._redis = client
        self._ttl = ttl_seconds
        self._prefix = key_prefix.rstrip(":")
        self._script = self._redis.register_script(LUA_TOKEN_BUCKET)

    def _key(self, key: str) -> str:
        return f"{self._prefix}:{key}"

    async def allow(self, *, key: str, limit: Limit) -> RateLimitResult:
        now = time.time()
        redis_key = self._key(key)

        allowed, remaining, retry_after = await self._script(
            keys=[redis_key],
            args=[
                str(now),
                str(limit.capacity),
                str(limit.refill_rate_per_sec),
                str(limit.tokens_per_request),
                str(self._ttl),
            ],
        )

        allowed = bool(int(allowed))
        remaining = int(remaining)
        retry_after = int(retry_after)

        return RateLimitResult(
            allowed=allowed,
            remaining=remaining,
            retry_after_seconds=max(retry_after, 0),
            limit=limit.capacity,
        )

    async def get_buckets(self) -> list[BucketSnapshot]:
        """
        Best-effort observability.
        This returns an empty list by default to avoid expensive key scans.
        """
        return []

    async def clear(self) -> None:
        """
        Best-effort clear.
        Only deletes keys matching this store's prefix.
        Intended for dev / admin usage.
        """
        pattern = f"{self._prefix}:*"
        async for key in self._redis.scan_iter(match=pattern):
            await self._redis.delete(key)


# exmaple setup:
# import redis.asyncio as redis
# from rate_limit.store.redis import RedisStore
# from rate_limit.limiter import RateLimiter

# redis_client = redis.from_url(
#     "redis://localhost:6379/0",
#     decode_responses=True,
# )

# store = RedisStore(
#     client=redis_client,
#     ttl_seconds=3600,
#     key_prefix="conversalia-rate",
# )

# limiter = RateLimiter(
#     store=store,
#     hooks=hooks,
# )
