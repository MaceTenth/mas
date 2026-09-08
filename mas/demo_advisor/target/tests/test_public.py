from copy import deepcopy

from policylog import authorize


def req(**changes):
    value = {"tenant": "acme", "user": "ana", "action": "deploy:read",
             "resource": "projects/red/api", "at": 100}
    value.update(changes)
    return value


def rule(rule_id="r1", **changes):
    value = {"id": rule_id, "tenant": "acme", "subject": "user:ana",
             "effect": "allow", "actions": ["deploy:read"],
             "resources": ["projects/red/api"]}
    value.update(changes)
    return value


def policy(*rules, groups=None):
    return {"groups": groups or {}, "rules": list(rules)}


def test_exact_user_rule_and_default_deny():
    p = policy(rule())
    assert authorize(p, req()) == {"allowed": True, "rule_id": "r1"}
    assert authorize(p, req(user="bo")) == {"allowed": False, "rule_id": None}


def test_nested_group_membership_and_cycles():
    groups = {"acme": {"eng": ["group:platform"],
                       "platform": ["user:ana", "group:eng"]}}
    p = policy(rule(subject="group:eng"), groups=groups)
    assert authorize(p, req()) == {"allowed": True, "rule_id": "r1"}


def test_segment_wildcards():
    p = policy(rule(actions=["deploy:*"], resources=["projects/**"]))
    assert authorize(p, req()) == {"allowed": True, "rule_id": "r1"}
    assert authorize(p, req(action="deploy:read:own")) == {"allowed": False, "rule_id": None}


def test_double_star_matches_zero_segments():
    p = policy(rule(resources=["projects/**"]))
    assert authorize(p, req(resource="projects")) == {"allowed": True, "rule_id": "r1"}


def test_time_window_is_half_open():
    p = policy(rule(valid_from=100, valid_until=110))
    assert authorize(p, req(at=100))["allowed"] is True
    assert authorize(p, req(at=110)) == {"allowed": False, "rule_id": None}


def test_inputs_are_not_mutated():
    p = policy(rule(), groups={"acme": {"eng": ["user:ana"]}})
    r = req()
    before = deepcopy((p, r))
    authorize(p, r)
    assert (p, r) == before
