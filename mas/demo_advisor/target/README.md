# policylog benchmark target

Implement `authorize()` in `src/policylog.py`. The task combines temporal
rules, nested cyclic groups, segment-aware glob matching, and deterministic
conflict resolution. Public tests exercise only the public contract; the
external `mas` gate scores both public semantics and the private deployment
profile.

Read `SPEC.md` before editing. Do not add dependencies or modify tests.
