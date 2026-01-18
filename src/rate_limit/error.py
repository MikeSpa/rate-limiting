from __future__ import annotations

from dataclasses import dataclass

from fastapi import HTTPException


@dataclass(frozen=True)
class RateLimitResult:
    allowed: bool
    remaining: int
    retry_after_seconds: int
    limit: int


def headers_from_result(result: RateLimitResult) -> dict[str, str]:
    headers: dict[str, str] = {
        "X-RateLimit-Limit": str(result.limit),
        "X-RateLimit-Remaining": str(max(result.remaining, 0)),
    }
    if not result.allowed:
        headers["Retry-After"] = str(max(result.retry_after_seconds, 1))
    return headers


class RateLimitExceeded(HTTPException):
    def __init__(
        self,
        *,
        detail: str = "Rate limit exceeded",
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(status_code=429, detail=detail, headers=headers or {})
