# rate-limit

A lightweight, extensible cost-aware rate-limiting engine for FastAPI applications.

Designed for:
- User / tenant aware limits
- Cost-based throttling (e.g. LLM endpoints, heavy processing, long background tasks)
- Clean observability
- In-memory or Redis backends, simple to start and easy to migrate to prod-grade
- Production-grade logging and extensibility

## Concepts

### Cost Classes
Routes declare a cost (e.g. `cheap`, `llm`) instead of hardcoded limits.

### Scopes
Limits can apply to:
- IP (for public routes)
- User
- Tenant

Multiple scopes can be evaluated per request.

## Usage

Declare the RateLimiter in core/
```python
limiter = RateLimiter(
    store=InMemoryStore(),
    policies=default_policies(),
    hooks=LoggingRateLimitHooks(app_logger),
)
```
Add the dependency to a route
```python
@router.post("/chat")
async def chat(
    _: None = rate_limit(limiter, cost="llm", scopes=[Scope.USER, Scope.TENANT]),
):
    ...
```

## Hooks

Hooks allow observing rate-limit decisions without affecting control flow.

Lifecycle
	•	on_allowed(...) is called after tokens are consumed
	•	on_rejected(...) is called when a request is blocked
	•	Hooks must be fast and non-blocking

Built-in hooks
	•	LoggingRateLimitHooks
	•	SampledLoggingHooks
	•	CompositeRateLimitHooks

Example:
```python
hooks = CompositeRateLimitHooks([
    LoggingRateLimitHooks(logger),
    SampledLoggingHooks(logger, sample_rate=0.01),
])
```

## Observability

The limiter exposes a public observability API for inspecting buckets.
(Admin UI support)

Backends
	•	In-memory (single-instance)
	•	Redis (multi-instance) — planned

Design Principles
	•	Explicit configuration
	•	No global state
	•	No framework lock-in
	•	Observability as a first-class concern



## Comparison with limits/slowapi

| slowapi /limits | THIS |
|------|-----|
| Request-based | Cost-based |
| Per-route strings | Policy-driven |
| Stateless config | Subscription-aware |
| Minimal observability | First-class hooks |
| Generic | SaaS / LLM-oriented |


---

## Future RoadMap
- Redis backend
