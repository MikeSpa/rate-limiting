from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from starlette.requests import Request


@dataclass(frozen=True)
class ResolvedIdentity:
    ip: str
    user_id: str | None
    tenant_id: str | None


def default_ip_extractor(request: Request) -> str:
    """
    Best-effort client IP. If you sit behind a trusted proxy, configure
    your proxy headers / middleware properly (e.g., ProxyHeadersMiddleware).
    """
    client = request.client.host if request.client else "unknown"
    # Common reverse proxy header; only trust if your infra is configured correctly.
    xff = request.headers.get("x-forwarded-for")
    if xff:
        # left-most is original client in typical setups
        client = xff.split(",")[0].strip() or client
    return client


def default_user_id_extractor(request: Request) -> str | None:
    """
    Convention: your auth layer sets request.state.user_id after validating the JWT.
    """
    return getattr(request.state, "user_id", None)


def default_tenant_id_extractor(request: Request) -> str | None:
    """
    Convention: your tenant resolver sets request.state.tenant_id.
    """
    return getattr(request.state, "tenant_id", None)


class IdentityResolver:
    def __init__(
        self,
        ip_extractor: Callable[[Request], str] = default_ip_extractor,
        user_id_extractor: Callable[[Request], str | None] = default_user_id_extractor,
        tenant_id_extractor: Callable[
            [Request], str | None
        ] = default_tenant_id_extractor,
    ) -> None:
        self._ip_extractor = ip_extractor
        self._user_id_extractor = user_id_extractor
        self._tenant_id_extractor = tenant_id_extractor

    def resolve(self, request: Request) -> ResolvedIdentity:
        return ResolvedIdentity(
            ip=self._ip_extractor(request),
            user_id=self._user_id_extractor(request),
            tenant_id=self._tenant_id_extractor(request),
        )
