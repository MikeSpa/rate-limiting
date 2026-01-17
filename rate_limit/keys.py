from __future__ import annotations


def parse_bucket_key(key: str) -> dict[str, str | None]:
    parts = key.split(":")

    def get_after(label: str) -> str | None:
        try:
            idx = parts.index(label)
            return parts[idx + 1] if idx + 1 < len(parts) else None
        except ValueError:
            return None

    return {
        "scope": get_after("scope"),
        "scope_id": get_after("scope") and get_after("scope_id") or get_after("scope"),
        "cost": get_after("cost"),
    }
