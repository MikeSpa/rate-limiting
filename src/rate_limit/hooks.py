from __future__ import annotations

from collections.abc import Iterable

"""
Hook lifecycle
	•	on_allowed(...) is called **after tokens are consumed**
	•	on_rejected(...) is called **when a request is blocked**
	•	Hooks:
	•	Are synchronous
	•	Must not block
	•	Must not raise
	•	Should be fast
	•	Hooks receive observability data only, not control flow
"""


class RateLimitHooks:
    """
    Hooks for the rate limiter.
    Can be used to logs, add alerting, or any other custom logic like basic billing, etc.
    """

    def on_allowed(
        self,
        *,
        key: str,
        scope: str | None,
        cost: str,
        remaining: float,
        request_id: str | None,
    ) -> None:
        pass

    def on_rejected(
        self,
        *,
        key: str,
        scope: str | None,
        cost: str,
        retry_after: int,
        request_id: str | None,
    ) -> None:
        pass


class CompositeRateLimitHooks(RateLimitHooks):
    def __init__(self, hooks: Iterable[RateLimitHooks]):
        self._hooks = list[RateLimitHooks](hooks)

    def on_allowed(
        self,
        *,
        key: str,
        scope: str | None,
        cost: str,
        remaining: float,
        request_id: str | None,
    ) -> None:
        for h in self._hooks:
            h.on_allowed(
                key=key,
                scope=scope,
                cost=cost,
                remaining=remaining,
                request_id=request_id,
            )

    def on_rejected(
        self,
        *,
        key: str,
        scope: str | None,
        cost: str,
        retry_after: int,
        request_id: str | None,
    ) -> None:
        for h in self._hooks:
            h.on_rejected(
                key=key,
                scope=scope,
                cost=cost,
                retry_after=retry_after,
                request_id=request_id,
            )


class NoopRateLimitHooks(RateLimitHooks):
    pass
