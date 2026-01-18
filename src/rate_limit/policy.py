from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Scope(str, Enum):
    IP = "ip"
    USER = "user"
    TENANT = "tenant"


class CostClass(str, Enum):
    CHEAP = "cheap"
    MEDIUM = "medium"
    LLM = "llm"


@dataclass(frozen=True)
class Limit:
    """
    Token-bucket parameters:
      - capacity: max tokens in bucket
      - refill_rate_per_sec: tokens added per second
      - tokens_per_request: how many tokens each request consumes (default 1)
    """

    capacity: int
    refill_rate_per_sec: float
    tokens_per_request: int = 1

    @staticmethod
    def per_minute(capacity: int, tokens_per_request: int = 1) -> Limit:
        return Limit(
            capacity=capacity,
            refill_rate_per_sec=capacity / 60.0,
            tokens_per_request=tokens_per_request,
        )

    @staticmethod
    def per_hour(capacity: int, tokens_per_request: int = 1) -> Limit:
        return Limit(
            capacity=capacity,
            refill_rate_per_sec=capacity / 3600.0,
            tokens_per_request=tokens_per_request,
        )

    @staticmethod
    def per_day(capacity: int, tokens_per_request: int = 1) -> Limit:
        return Limit(
            capacity=capacity,
            refill_rate_per_sec=capacity / 86400.0,
            tokens_per_request=tokens_per_request,
        )


# Policy type:
#   policies[scope][cost_class] = Limit
Policies = dict[Scope, dict[str, Limit]]


def default_policies() -> dict[Scope, dict[str, Limit]]:
    """
    Sensible defaults. Override in each app by passing `policies=...` to RateLimiter.
    """
    return {
        Scope.IP: {
            CostClass.CHEAP.value: Limit.per_minute(120),
            CostClass.MEDIUM.value: Limit.per_minute(60),
            CostClass.LLM.value: Limit.per_minute(10),
            # CostClass.LLM.value: Limit.per_minute(2),
        },
        Scope.USER: {
            # CostClass.CHEAP.value: Limit.per_hour(2_000),
            # CostClass.MEDIUM.value: Limit.per_hour(1_000),
            CostClass.CHEAP.value: Limit.per_day(2_000),
            CostClass.MEDIUM.value: Limit.per_day(1_000),
            CostClass.LLM.value: Limit.per_minute(30),
        },
        Scope.TENANT: {
            CostClass.CHEAP.value: Limit.per_day(50_000),
            CostClass.MEDIUM.value: Limit.per_day(20_000),
            CostClass.LLM.value: Limit.per_day(2_000),
        },
    }


def get_limit(
    policies: Policies,
    scope: Scope,
    cost: str,
) -> Limit | None:
    return policies.get(scope, {}).get(cost)
