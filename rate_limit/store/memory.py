from __future__ import annotations

import asyncio
import math
import time
from dataclasses import dataclass

from rate_limit.error import RateLimitResult
from rate_limit.policy import Limit
from rate_limit.store.base import RateLimitStore
from rate_limit.observability import BucketSnapshot


@dataclass
class _Bucket:
    tokens: float
    last_ts: float
    # simple lazy expiry
    expires_at: float


class InMemoryStore(RateLimitStore):
    """
    In-memory token bucket store.
    Safe for single-instance deployments only.
    """

    def __init__(self, *, ttl_seconds: int = 3600) -> None:
        self._ttl_seconds = ttl_seconds
        self._buckets: dict[str, _Bucket] = {}
        self._lock = asyncio.Lock()

    async def allow(self, *, key: str, limit: Limit) -> RateLimitResult:
        now = time.time()
        async with self._lock:
            b = self._buckets.get(key)

            # Lazy eviction
            if b and b.expires_at <= now:
                b = None
                self._buckets.pop(key, None)

            if b is None:
                # start full
                b = _Bucket(
                    tokens=float(limit.capacity),
                    last_ts=now,
                    expires_at=now + self._ttl_seconds,
                )
                self._buckets[key] = b

            # Refill
            elapsed = max(0.0, now - b.last_ts)
            b.tokens = min(
                float(limit.capacity), b.tokens + elapsed * limit.refill_rate_per_sec
            )
            b.last_ts = now
            b.expires_at = now + self._ttl_seconds

            cost = float(limit.tokens_per_request)
            if b.tokens >= cost:
                b.tokens -= cost
                remaining = int(math.floor(b.tokens))
                return RateLimitResult(
                    allowed=True,
                    remaining=remaining,
                    retry_after_seconds=0,
                    limit=limit.capacity,
                )

            # Not enough tokens: compute time until we can satisfy the request
            needed = cost - b.tokens
            if limit.refill_rate_per_sec <= 0:
                retry = self._ttl_seconds
            else:
                retry = int(math.ceil(needed / limit.refill_rate_per_sec))
            remaining = int(math.floor(b.tokens))
            return RateLimitResult(
                allowed=False,
                remaining=remaining,
                retry_after_seconds=max(retry, 1),
                limit=limit.capacity,
            )

    async def get_buckets(self) -> list[BucketSnapshot]:
        return [
            BucketSnapshot(
                key=key,
                tokens=b.tokens,
                last_updated=b.last_ts,
                expires_at=b.expires_at,
            )
            for key, b in self._buckets.items()
        ]

    async def clear(self) -> None:
        self._buckets.clear()
