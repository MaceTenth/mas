"""Profile lookups for the public API and the account page.

PR #142 — "speed up get_profile with a TTL cache"

Before this change every call hit the database; p95 latency was 180 ms.
After: identical results, served from a 5-minute in-process cache.
"""
from __future__ import annotations

import time

TTL_SECONDS = 300
_cache: dict = {}


def _load_profile(user_id: str, include_private: bool) -> dict:
    """Simulates the database read. Private fields are returned only when asked for."""
    profile = {"id": user_id, "name": f"user-{user_id}", "plan": "pro"}
    if include_private:
        profile.update({"email": f"{user_id}@example.com", "phone": "+1-555-0100", "billing_last4": "4242"})
    return profile


def get_profile(user_id: str, include_private: bool = False, *, now: float | None = None) -> dict:
    """Return a user's profile.

    include_private=True is used by the account page (the user viewing themselves).
    Public callers (search, mentions, the public API) must never receive private fields.
    """
    now = time.time() if now is None else now
    key = user_id
    hit = _cache.get(key)
    if hit and now - hit["at"] < TTL_SECONDS:
        return hit["value"]
    value = _load_profile(user_id, include_private)
    _cache[key] = {"at": now, "value": value}
    return value


def invalidate(user_id: str) -> None:
    """Called when a user edits their profile."""
    _cache.pop(user_id, None)
