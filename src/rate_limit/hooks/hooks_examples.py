from __future__ import annotations

from rate_limit.hooks import RateLimitHooks


class TenantBillingHooks(RateLimitHooks):
    def __init__(self, billing_client) -> None:
        self.billing = billing_client

    def on_allowed(
        self,
        *,
        key: str,
        scope: str | None,
        cost: str,
        remaining: float,
        request_id: str | None,
    ) -> None:
        if scope != "tenant":
            return

        tenant_id = self._extract_tenant_from_key(key)

        self.billing.record_usage(
            tenant_id=tenant_id,
            cost_class=cost,
            units=1,
            request_id=request_id,
        )


# then:
# hooks = CompositeRateLimitHooks([
#     LoggingRateLimitHooks(logger),
#     SampledLoggingHooks(logger, 0.01),
#     TenantBillingHooks(billing_client),
# ])
