from __future__ import annotations

from abc import ABC, abstractmethod

from rate_limit.error import RateLimitResult
from rate_limit.observability import BucketSnapshot
from rate_limit.policy import Limit


class RateLimitStore(ABC):
    """
    Store enforces token-bucket semantics for a given key+limit.
    Key should encode scope/id/cost so it is debuggable.
    """

    @abstractmethod
    async def allow(self, *, key: str, limit: Limit) -> RateLimitResult:
        raise NotImplementedError

    async def get_buckets(self) -> list[BucketSnapshot]:
        """
        Observability hook.
        Stores may return empty list if unsupported.
        """
        return []

    async def clear(self) -> None:
        """
        Clear all buckets (best-effort).
        """
        return None
