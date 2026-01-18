from __future__ import annotations

from collections.abc import Sequence

from fastapi import Depends

from rate_limit.limiter import RateLimiter
from rate_limit.policy import CostClass, Scope


def rate_limit(
    limiter: RateLimiter,
    *,
    cost: str | CostClass,
    scopes: Sequence[Scope],
):
    """
    Usage:
      @router.post("/chat")
      async def chat(_: None = Depends(rate_limit(limiter, cost="llm", scopes=[Scope.USER, Scope.TENANT]))):
          ...
    """
    return Depends(limiter.require(cost=cost, scopes=scopes))
