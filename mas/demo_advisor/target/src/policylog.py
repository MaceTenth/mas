"""Incomplete temporal authorization engine for the adviser benchmark."""
from __future__ import annotations


def authorize(policy: dict, request: dict) -> dict:
    """Return ``{"allowed": bool, "rule_id": str | None}`` for *request*.

    The starter handles only exact rules for a user. It deliberately ignores
    groups, time windows, wildcards, authority, priority, and conflict
    resolution. Replace it with the complete implementation from SPEC.md.
    """
    tenant = request["tenant"]
    subject = f"user:{request['user']}"
    action = request["action"]
    resource = request["resource"]

    for rule in policy.get("rules", []):
        if (rule.get("tenant") == tenant
                and rule.get("subject") == subject
                and action in rule.get("actions", [])
                and resource in rule.get("resources", [])):
            return {"allowed": rule.get("effect") == "allow", "rule_id": rule.get("id")}
    return {"allowed": False, "rule_id": None}
