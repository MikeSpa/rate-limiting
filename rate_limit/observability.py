from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BucketSnapshot:
    """
    Store-level snapshot.
    This reflects *actual bucket state*, not policy.
    The store is responsible for storing the bucket state. Doesnt care about capacity, policy, scope, cost classes,...
    """

    key: str
    tokens: float
    last_updated: float
    expires_at: float


@dataclass(frozen=True)
class BucketView:
    """
    Limiter-level enriched view.
    This is what admin / UI / logs consume.
    """

    key: str
    scope: str | None
    scope_id: str | None
    cost: str | None

    tokens: float
    capacity: int | None
    remaining: float

    last_updated: float
    expires_at: float
