from __future__ import annotations

import logging
import random

from rate_limit.hooks import RateLimitHooks

# logger = logging.getLogger("rate_limit")
# logger = logging.getLogger("apiname.rate_limit")


class LoggingRateLimitHooks(RateLimitHooks):
    """
    Logging hooks for the rate limiter.
    Premade custom logging for user using logging library.
    Reference implementation and Default adapter.
    """

    def __init__(self, logger: logging.Logger):
        self._logger = logger

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


class SampledLoggingHooks(RateLimitHooks):
    """
    Sampled logging hooks for the rate limiter.
    Logs a sample of the allowed but always logs rejected events.
    """

    def __init__(self, logger: logging.Logger, sample_rate: float = 0.01):
        self._logger = logger
        self._sample_rate = sample_rate

    def on_allowed(
        self,
        *,
        key: str,
        scope: str | None,
        cost: str,
        remaining: float,
        request_id: str | None,
    ) -> None:
        if random.random() < self._sample_rate:
            self._logger.info(
                "rate_limit.allowed.sampled",
                extra={
                    "bucket_key": key,
                    "scope": scope,
                    "cost": cost,
                    "remaining": remaining,
                    "request_id": request_id,
                },
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
        # Always log rejections
        self._logger.warning(
            "rate_limit.rejected",
            extra={
                "bucket_key": key,
                "scope": scope,
                "cost": cost,
                "retry_after": retry_after,
                "request_id": request_id,
            },
        )
