from __future__ import annotations

from abc import ABC, abstractmethod

from rate_limit.error import RateLimitResult
from rate_limit.observability import BucketSnapshot
from rate_limit.policy import Limit


class RateLimitStore(ABC):
    """
    The stor is the persistence and concurrency layer for rate limiting.
    Given a key and a Limit, decide whether a request is allowed and update the bucket (numbers+ts) state atomically.

    Store enforces token-bucket semantics for a given key+limit.
    Key should encode scope/id/cost so it is debuggable.
    Store is obviously scope and policy-agnostic (and framework-agnostic)
    """

    @abstractmethod
    async def allow(self, *, key: str, limit: Limit) -> RateLimitResult:
        raise NotImplementedError

    async def get_buckets(self) -> list[BucketSnapshot]:
        """
        Observability hook.
        Stores may return empty list if unsupported, dont want to do that for Redis backend
        """
        return []

    async def clear(self) -> None:
        """
        Clear all buckets (best-effort).
        """
        return None
