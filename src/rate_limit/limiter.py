from __future__ import annotations

from collections.abc import Callable, Coroutine, Sequence
from dataclasses import dataclass
from typing import Any

from starlette.requests import Request

from rate_limit.error import RateLimitExceeded, headers_from_result
from rate_limit.hooks import RateLimitHooks
from rate_limit.identity import IdentityResolver
from rate_limit.keys import parse_bucket_key
from rate_limit.observability import BucketView
from rate_limit.policy import (
    CostClass,
    Policies,
    Scope,
    default_policies,
    get_limit,
)
from rate_limit.store.base import RateLimitStore


@dataclass(frozen=True)
class RateLimitContext:
    cost: str
    scopes: Sequence[Scope]


class RateLimiter:
    """
    Rate limiter that checks if a request is allowed based on the rate limit policies.
    It uses a store to store the rate limit buckets and a resolver to resolve the identity of the request.
    It uses a policies to define the rate limit policies.
    It uses a key namespace to prefix the keys of the rate limit buckets.
    It uses a hooks to hook into the rate limit process, for logging and other logic like billing.
        The rate limiter emmits two events, on_allowed and on_rejected,
        which are called when a request is allowed or rejected.
    """

    def __init__(
        self,
        *,
        store: RateLimitStore,
        policies: Policies | None = None,
        identity_resolver: IdentityResolver | None = None,
        key_namespace: str = "",
        hooks: RateLimitHooks | None = None,
    ) -> None:
        self._store = store
        self._policies: Policies = policies or default_policies()
        self._resolver = identity_resolver or IdentityResolver()
        self._ns = key_namespace.strip(":")
        self._hooks = hooks or RateLimitHooks()

    def _key(self, *, scope: Scope, scope_id: str, cost: str) -> str:
        # You want keys that are readable in logs/Redis.
        # TODO look into # for ids in redis
        # Example: "appA:scope:user:123:cost:llm"
        parts = []
        if self._ns:
            parts.append(self._ns)
        parts.extend(["scope", scope.value, scope_id, "cost", cost])
        return ":".join(parts)

    # For now this lib is not framework agnostic,
    # so we need to use starlette/FastAPI's Request object.
    async def check(self, *, request: Request, cost: str, scopes: Sequence[Scope]) -> None:
        ident = self._resolver.resolve(request)

        # Build scope -> id mapping
        scope_ids = {
            Scope.IP: ident.ip,
            Scope.USER: ident.user_id,
            Scope.TENANT: ident.tenant_id,
        }

        request_id = getattr(request.state, "request_id", None)

        # Evaluate in given order; fail fast. Typical order:
        # tenant -> user -> ip (or ip first for public)
        for scope in scopes:
            scope_id = scope_ids.get(scope)
            if not scope_id:
                # If scope requested but not resolvable, treat as "not applicable"
                # (e.g. tenant scope on a non-tenant route)
                continue

            limit = get_limit(self._policies, scope, cost)
            if not limit:
                continue  # no policy means "unlimited" for that scope+cost

            key = self._key(scope=scope, scope_id=str(scope_id), cost=cost)
            result = await self._store.allow(key=key, limit=limit)

            if not result.allowed:
                headers = headers_from_result(result)
                self._hooks.on_rejected(
                    key=key,
                    scope=scope,
                    cost=cost,
                    retry_after=result.retry_after_seconds,
                    request_id=request_id,
                )
                raise RateLimitExceeded(headers=headers)
            else:
                self._hooks.on_allowed(
                    key=key,
                    scope=scope,
                    cost=cost,
                    remaining=result.remaining,
                    request_id=request_id,
                )

        # Allowed (no exception)

    def require(
        self,
        *,
        cost: str | CostClass,
        scopes: Sequence[Scope],
    ) -> Callable[[Request], Coroutine[Any, Any, None]]:
        """
        Returns a callable suitable for FastAPI Depends, but kept here for reuse.
        """
        cost_value = cost.value if isinstance(cost, CostClass) else str(cost)

        async def _dep(request: Request) -> None:
            await self.check(request=request, cost=cost_value, scopes=scopes)

        return _dep

    def get_policies(self) -> Policies:
        """Get the current rate limit policies."""
        return self._policies

    async def get_bucket_views(self) -> list[BucketView]:
        """
        Public observability API.
        """
        snapshots = await self._store.get_buckets()
        views: list[BucketView] = []

        for snap in snapshots:
            parsed = parse_bucket_key(snap.key)

            capacity = None
            if parsed["scope"] and parsed["cost"]:
                scope_enum = Scope(parsed["scope"])
                limit = self._policies.get(scope_enum, {}).get(parsed["cost"])
                if limit:
                    capacity = limit.capacity

            views.append(
                BucketView(
                    key=snap.key,
                    scope=parsed["scope"],
                    scope_id=parsed["scope_id"],
                    cost=parsed["cost"],
                    tokens=snap.tokens,
                    remaining=snap.tokens,
                    capacity=capacity,
                    last_updated=snap.last_updated,
                    expires_at=snap.expires_at,
                )
            )

        return views

    async def clear_buckets(self) -> None:
        await self._store.clear()
