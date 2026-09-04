# PR #142 — speed up `get_profile` with a TTL cache

**Author:** platform team · **Files:** `svc/profile_cache.py`

## Why
`get_profile` is the hottest read in the service (search results, mentions, the account page).
Every call hit the database; p95 was 180 ms. Profiles change rarely, so a 5-minute in-process
cache is safe and brings p95 under 5 ms in staging.

## What changed
- Added a module-level `_cache` dict and `TTL_SECONDS = 300`.
- `get_profile` checks the cache first and falls back to `_load_profile`.
- Added `invalidate(user_id)`, called from the profile-edit handler.
- `now` is injectable for tests.

## Testing
Manually verified in staging: the account page and public search both render correctly,
and the second call is served from cache. There are no automated tests for the cache path yet;
they will come in a follow-up.

## Review question
Does this change introduce a bug that would affect production — a correctness or security
problem, not style? Answer YES or NO with the location and one concrete failing scenario.
