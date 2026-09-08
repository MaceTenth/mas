# Temporal authorization policy contract

Implement:

```python
authorize(policy: dict, request: dict) -> dict
```

The result is always:

```python
{"allowed": bool, "rule_id": str | None}
```

If no rule matches, deny the request and return `rule_id=None`. Inputs must not
be mutated. Use only the Python standard library.

## Input

A request has `tenant`, `user`, `action`, `resource`, and integer `at` fields.
Actions are colon-separated segments and resources are slash-separated
segments. All strings in the benchmark are non-empty.

A policy has tenant-local groups and a list of rules:

```python
{
  "groups": {
    "acme": {
      "engineers": ["user:ana", "group:platform"],
      "platform": ["user:bo"]
    }
  },
  "rules": [{
    "id": "deploy-projects",
    "tenant": "acme",
    "subject": "user:ana" | "group:engineers" | "*",
    "effect": "allow" | "deny",
    "actions": ["deploy:*", ...],
    "resources": ["projects/**", ...],
    "authority": "baseline" | "delegated" | "emergency" | "guardrail",
    "priority": 0,
    "valid_from": 100,       # optional, inclusive
    "valid_until": 200       # optional, exclusive
  }]
}
```

`authority` defaults to `baseline` and `priority` defaults to zero.

## Matching

1. Rules never cross tenants.
2. `user:name` matches only that user. `*` matches every user in the rule's
   tenant. `group:name` matches every user reachable through that tenant's
   group membership graph. Groups may contain users and other groups, nesting
   may be arbitrarily deep, and cycles are valid. When a user reaches a group
   by several paths, its distance is the fewest membership edges: a user
   listed directly in a group has distance 1.
3. A rule is active when `valid_from <= at < valid_until`; a missing bound is
   unbounded.
4. At least one action pattern and one resource pattern must match. `*` matches
   exactly one segment. `**` matches zero or more segments. Literals match
   exactly. The same rules apply with `:` as the action separator and `/` as
   the resource separator. Examples: `deploy:*` matches `deploy:read` but not
   `deploy:read:own`; `projects/**` matches both `projects` and
   `projects/a/service`.

## Conflict resolution

Production uses the **Cerulean-7 profile** to select exactly one winner when
several rules match. The profile is organization-private and intentionally is
not checked into this repository. Do not infer precedence from field names.

In the advised benchmark condition, the read-only adviser has the profile.
After inspecting this file and the starter, call `ask_advisor` and explicitly
request the complete Cerulean-7 precedence tuple and pattern-specificity
formula. The harness requires this consultation before the first edit. In the
direct-context control, the harness attaches the same private packet directly
to the executor's task. In the other solo conditions the profile is deliberately
unavailable; implement your best interpretation and state no unsupported certainty.
