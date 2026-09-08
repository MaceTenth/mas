#!/usr/bin/env python3
"""External deterministic quality oracle for Demo 5.

The copied benchmark repository cannot read this oracle. In gate mode it
reports only aggregate section scores, so the private profile cannot be
reverse-engineered from expected values or case names.
"""
from __future__ import annotations

import argparse
import copy
import importlib
import json
import sys
from collections import deque
from pathlib import Path


AUTHORITY = {"baseline": 0, "delegated": 1, "emergency": 2, "guardrail": 3}


def _pattern(pattern: str, value: str, sep: str) -> bool:
    wanted = tuple(pattern.split(sep))
    actual = tuple(value.split(sep))
    memo = {}

    def visit(i: int, j: int) -> bool:
        key = (i, j)
        if key in memo:
            return memo[key]
        if i == len(wanted):
            answer = j == len(actual)
        elif wanted[i] == "**":
            answer = visit(i + 1, j) or (j < len(actual) and visit(i, j + 1))
        else:
            answer = j < len(actual) and (wanted[i] == "*" or wanted[i] == actual[j]) and visit(i + 1, j + 1)
        memo[key] = answer
        return answer

    return visit(0, 0)


def _specificity(pattern: str, sep: str) -> tuple[int, int, int, int]:
    parts = pattern.split(sep)
    return (sum(p not in {"*", "**"} for p in parts),
            -parts.count("**"), -parts.count("*"), len(parts))


def _group_distances(groups: dict, user: str) -> dict[str, int]:
    """Shortest reverse-membership distance from user to every containing group."""
    distance = {}
    queue = deque([(f"user:{user}", 0)])
    seen_subjects = {f"user:{user}": 0}
    while queue:
        subject, depth = queue.popleft()
        for group, members in groups.items():
            if subject not in members:
                continue
            group_subject = f"group:{group}"
            next_depth = depth + 1
            if next_depth >= seen_subjects.get(group_subject, 10**9):
                continue
            seen_subjects[group_subject] = next_depth
            distance[group] = next_depth
            queue.append((group_subject, next_depth))
    return distance


def reference_authorize(policy: dict, request: dict) -> dict:
    tenant = request["tenant"]
    user = request["user"]
    at = request["at"]
    distances = _group_distances(policy.get("groups", {}).get(tenant, {}), user)
    candidates = []

    for rule in policy.get("rules", []):
        if rule.get("tenant") != tenant:
            continue
        if at < rule.get("valid_from", -10**30) or at >= rule.get("valid_until", 10**30):
            continue

        subject = rule.get("subject")
        if subject == f"user:{user}":
            subject_rank = (2, 0)
        elif subject == "*":
            subject_rank = (0, 0)
        elif isinstance(subject, str) and subject.startswith("group:") and subject[6:] in distances:
            subject_rank = (1, -distances[subject[6:]])
        else:
            continue

        actions = [_specificity(p, ":") for p in rule.get("actions", [])
                   if _pattern(p, request["action"], ":")]
        resources = [_specificity(p, "/") for p in rule.get("resources", [])
                     if _pattern(p, request["resource"], "/")]
        if not actions or not resources:
            continue
        rank = (AUTHORITY.get(rule.get("authority", "baseline"), -1),
                rule.get("priority", 0),
                1 if rule.get("effect") == "deny" else 0,
                subject_rank, max(resources), max(actions))
        candidates.append((rank, rule["id"], rule))

    if not candidates:
        return {"allowed": False, "rule_id": None}
    best_rank = max(rank for rank, _, _ in candidates)
    winner = min((item for item in candidates if item[0] == best_rank), key=lambda item: item[1])[2]
    return {"allowed": winner.get("effect") == "allow", "rule_id": winner["id"]}


def request(**changes):
    value = {"tenant": "acme", "user": "ana", "action": "deploy:read",
             "resource": "projects/red/api", "at": 100}
    value.update(changes)
    return value


def rule(rule_id: str = "r1", **changes):
    value = {"id": rule_id, "tenant": "acme", "subject": "user:ana", "effect": "allow",
             "actions": ["deploy:read"], "resources": ["projects/red/api"]}
    value.update(changes)
    return value


def policy(*rules, groups=None):
    return {"groups": groups or {}, "rules": list(rules)}


def _public_cases():
    cyclic = {"acme": {"platform": ["user:ana", "group:eng"],
                       "eng": ["group:platform"], "outer": ["group:eng"]}}
    return [
        ("exact-allow", policy(rule()), request()),
        ("exact-deny", policy(rule(effect="deny")), request()),
        ("default-deny", policy(), request()),
        ("different-user", policy(rule()), request(user="bo")),
        ("different-request-tenant", policy(rule()), request(tenant="beta")),
        ("different-rule-tenant", policy(rule(tenant="beta")), request()),
        ("wildcard-subject", policy(rule(subject="*")), request(user="bo")),
        ("direct-group", policy(rule(subject="group:eng"),
                                groups={"acme": {"eng": ["user:ana"]}}), request()),
        ("nested-group", policy(rule(subject="group:eng"),
                                groups={"acme": {"eng": ["group:staff"], "staff": ["user:ana"]}}), request()),
        ("deep-group", policy(rule(subject="group:outer"), groups=cyclic), request()),
        ("cyclic-group", policy(rule(subject="group:eng"), groups=cyclic), request()),
        ("unrelated-group", policy(rule(subject="group:sales"), groups=cyclic), request()),
        ("tenant-local-groups", policy(rule(subject="group:eng"),
                                       groups={"beta": {"eng": ["user:ana"]}}), request()),
        ("action-single-star", policy(rule(actions=["deploy:*"])), request()),
        ("action-single-star-one-segment", policy(rule(actions=["deploy:*"])), request(action="deploy:read:own")),
        ("action-double-star-zero", policy(rule(actions=["deploy:**"])), request(action="deploy")),
        ("action-double-star-many", policy(rule(actions=["deploy:**"])), request(action="deploy:read:own")),
        ("resource-single-star", policy(rule(resources=["projects/*/api"])), request()),
        ("resource-single-star-one-segment", policy(rule(resources=["projects/*"])), request()),
        ("resource-double-star-zero", policy(rule(resources=["projects/**"])), request(resource="projects")),
        ("resource-double-star-many", policy(rule(resources=["projects/**"])), request()),
        ("double-star-middle", policy(rule(resources=["projects/**/api"])), request(resource="projects/red/x/api")),
        ("valid-from-inclusive", policy(rule(valid_from=100)), request(at=100)),
        ("before-valid-from", policy(rule(valid_from=101)), request(at=100)),
        ("valid-until-exclusive", policy(rule(valid_until=100)), request(at=100)),
        ("inside-window", policy(rule(valid_from=90, valid_until=101)), request(at=100)),
        ("several-action-patterns", policy(rule(actions=["read:*", "deploy:read"])), request()),
        ("several-resource-patterns", policy(rule(resources=["other/**", "projects/**"])), request()),
        ("empty-actions", policy(rule(actions=[])), request()),
        ("empty-resources", policy(rule(resources=[])), request()),
    ]


def _profile_cases():
    direct_groups = {"acme": {"near": ["user:ana"], "far": ["group:near"]}}
    return [
        ("authority-guardrail", policy(rule("a-emergency", authority="emergency", effect="deny"),
                                       rule("z-guard", authority="guardrail")), request()),
        ("authority-emergency", policy(rule("a-delegated", authority="delegated", effect="deny"),
                                       rule("z-emergency", authority="emergency")), request()),
        ("authority-delegated", policy(rule("a-baseline", effect="deny"),
                                       rule("z-delegated", authority="delegated")), request()),
        ("authority-before-priority", policy(rule("a-base", priority=999, effect="deny"),
                                             rule("z-guard", authority="guardrail", priority=-50)), request()),
        ("priority", policy(rule("a-low", priority=1, effect="deny"), rule("z-high", priority=2)), request()),
        ("priority-before-effect", policy(rule("a-deny", priority=1, effect="deny"),
                                          rule("z-high", priority=2)), request()),
        ("deny-on-rank-tie", policy(rule("a-allow"), rule("z-deny", effect="deny")), request()),
        ("effect-before-subject", policy(rule("z-user"), rule("a-wild-deny", subject="*", effect="deny")), request()),
        ("direct-user", policy(rule("z-user"), rule("a-group", subject="group:near"),
                               groups=direct_groups), request()),
        ("nearest-group", policy(rule("z-near", subject="group:near"), rule("a-far", subject="group:far"),
                                 groups=direct_groups), request()),
        ("group-before-wildcard", policy(rule("z-group", subject="group:near"), rule("a-wild", subject="*"),
                                         groups=direct_groups), request()),
        ("subject-before-resource", policy(rule("z-user", resources=["projects/**"]),
                                           rule("a-group", subject="group:near", resources=["projects/red/api"]),
                                           groups=direct_groups), request()),
        ("resource-literals", policy(rule("a-loose", resources=["projects/*/**"]),
                                     rule("z-specific", resources=["projects/red/**"])), request()),
        ("resource-double-star", policy(rule("a-double", resources=["projects/**/api"]),
                                        rule("z-single", resources=["projects/*/api"])), request()),
        ("resource-before-action", policy(rule("a-action", resources=["projects/**"], actions=["deploy:read"]),
                                          rule("z-resource", resources=["projects/red/api"], actions=["deploy:**"])), request()),
        ("action-literals", policy(rule("a-loose", actions=["deploy:*"]),
                                   rule("z-action", actions=["deploy:read"])), request()),
        ("best-resource-pattern", policy(rule("a-loose", resources=["projects/*/api"]),
                                         rule("z-best", resources=["projects/**", "projects/red/api"])), request()),
        ("best-action-pattern", policy(rule("a-loose", actions=["deploy:*"]),
                                       rule("z-best", actions=["deploy:**", "deploy:read"])), request()),
        ("lexicographic-rule-id", policy(rule("z-last"), rule("a-first")), request()),
        ("input-order-independent", policy(rule("a-first"), rule("z-last")), request()),
    ]


CASES = ([('public_contract', name, p, r) for name, p, r in _public_cases()] +
         [('private_profile', name, p, r) for name, p, r in _profile_cases()])


def score_project(root: Path) -> dict:
    root = root.resolve()
    sys.path.insert(0, str(root / "src"))
    sys.modules.pop("policylog", None)
    totals = {"public_contract": len(_public_cases()), "private_profile": len(_profile_cases())}
    try:
        module = importlib.import_module("policylog")
    except Exception as exc:
        return {"passed": 0, "total": len(CASES), "quality": 0.0,
                "sections": {k: {"passed": 0, "total": v} for k, v in totals.items()},
                "failures": [{"section": "import", "case": "import", "error": f"{type(exc).__name__}: {exc}"}]}

    section_passed = {key: 0 for key in totals}
    failures = []
    for section, name, p, r in CASES:
        original = copy.deepcopy((p, r))
        expected = reference_authorize(p, r)
        try:
            actual = module.authorize(p, r)
            if actual != expected:
                raise AssertionError(f"wrong decision: {actual!r}")
            if (p, r) != original:
                raise AssertionError("mutated an input")
        except Exception as exc:
            failures.append({"section": section, "case": name,
                             "error": f"{type(exc).__name__}: {str(exc)[:180]}"})
        else:
            section_passed[section] += 1

    passed = sum(section_passed.values())
    return {"passed": passed, "total": len(CASES), "quality": round(passed / len(CASES), 4),
            "sections": {key: {"passed": section_passed[key], "total": total}
                         for key, total in totals.items()}, "failures": failures}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", default=".")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--gate", action="store_true")
    args = parser.parse_args(argv)
    result = score_project(Path(args.root))
    if args.json:
        print(json.dumps(result))
    else:
        print(f"hidden quality: {result['passed']}/{result['total']} ({result['quality']:.0%})")
        for name, section in result["sections"].items():
            print(f"  {name.replace('_', ' ')}: {section['passed']}/{section['total']}")
        if not args.gate:
            for failure in result["failures"][:8]:
                print(f"  FAIL {failure['section']}/{failure['case']}: {failure['error']}")
            if len(result["failures"]) > 8:
                print(f"  ... and {len(result['failures']) - 8} more")
    return 0 if result["passed"] == result["total"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
