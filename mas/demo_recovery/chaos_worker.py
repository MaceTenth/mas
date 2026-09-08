#!/usr/bin/env python3
"""Deterministic unreliable workers for Demo 6.

The point is to exercise the real MAS recovery machinery without paying for an
LLM or hoping a model happens to fail in the desired way. Each invocation is a
normal ExecWorker subprocess in a real per-attempt worktree. Its behavior is
selected by the item id and attempt encoded in that worktree's directory name.
"""
from __future__ import annotations

import argparse
import json
import shlex
import sqlite3
import sys
import time
from pathlib import Path


def identity(cwd: Path) -> tuple[str, int]:
    item_id, sep, raw_attempt = cwd.name.rpartition("-a")
    if not sep or not raw_attempt.isdigit():
        raise SystemExit(f"cannot recover item/attempt from compartment {cwd.name!r}")
    return item_id, int(raw_attempt)


def write(cwd: Path, rel: str, text: str) -> None:
    path = cwd / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def command_check(python: str, verifier: str, case: str) -> str:
    return f"{shlex.quote(python)} {shlex.quote(verifier)} . {shlex.quote(case)}"


def write_plan(cwd: Path, python: str, verifier: str) -> None:
    check = lambda case: "cmd:" + command_check(python, verifier, case)
    items = [
        {"id": "heartbeat-survival", "title": "Survive longer than one lease", "brief": "Work for three seconds while heartbeats renew the two-second lease.",
         "check": check("heartbeat-survival"), "merge_paths": ["artifacts/heartbeat.txt"], "priority": 90},
        {"id": "gate-retry", "title": "Recover from a confident wrong answer", "brief": "The first fast agent will claim success with bad output; the gate must reject it and a stronger retry must repair it.",
         "check": check("gate-retry"), "merge_paths": ["artifacts/gate-retry.txt"], "priority": 85, "max_attempts": 2},
        {"id": "worker-crash", "title": "Recover from a worker process crash", "brief": "The first worker process exits non-zero; retry in a fresh compartment.",
         "check": check("worker-crash"), "merge_paths": ["artifacts/worker-crash.txt"], "priority": 80, "max_attempts": 2},
        {"id": "timeout-recovery", "title": "Recover from a stuck worker", "brief": "The first worker exceeds its time budget and is killed; the retry completes.",
         "check": check("timeout-recovery"), "merge_paths": ["artifacts/timeout.txt"], "priority": 75, "max_attempts": 2},
        {"id": "idempotent-first", "title": "Land a shared result", "brief": "Write the canonical shared result.",
         "check": check("idempotent"), "merge_paths": ["artifacts/idempotent.txt"], "priority": 70},
        {"id": "idempotent-second", "title": "Land the identical result again", "brief": "Write the same canonical result; landing should become a no-op.",
         "check": check("idempotent"), "merge_paths": ["artifacts/idempotent.txt"], "priority": 69, "depends_on": ["idempotent-first"]},
        {"id": "scoped-merge", "title": "Contain an out-of-scope write", "brief": "Produce the allowed artifact and an accidental extra file. Only the declared merge path may land.",
         "check": check("scoped-merge"), "merge_paths": ["artifacts/scoped.txt"], "priority": 65},
        {"id": "schema-gate", "title": "Verify structured output", "brief": "Produce a JSON manifest for the schema gate.",
         "check": "schema:artifacts/manifest.json", "merge_paths": ["artifacts/manifest.json"], "priority": 60,
         "meta": {"schema": {"required": ["status", "generation"], "properties": {"status": {"type": "string"}, "generation": {"type": "integer"}}}}},
        {"id": "lesson-source", "title": "Discover a recovery lesson", "brief": "Complete the task and publish the recovery token in the worker summary.",
         "check": check("lesson-source"), "merge_paths": ["artifacts/lesson-source.txt"], "priority": 55},
        {"id": "lesson-consumer", "title": "Use durable shared context", "brief": "Recover the token from LESSONS FROM EARLIER WORKERS in your prompt.",
         "check": check("lesson-consumer"), "merge_paths": ["artifacts/lesson-consumer.txt"], "priority": 54, "depends_on": ["lesson-source"]},
        {"id": "permanent-failure", "title": "Open the circuit breaker", "brief": "This dependency is irrecoverably broken. Preserve evidence and park it after two attempts.",
         "check": check("permanent-failure"), "merge_paths": ["artifacts/permanent.txt"], "priority": 50, "max_attempts": 2},
        # Deliberately malformed: the spawner must reject untrusted plan entries.
        {"id": "malformed", "title": "Malformed generated item", "brief": "Missing its check on purpose."},
    ]
    write(cwd, "PLAN.json", json.dumps({"items": items}, indent=2) + "\n")


def load_events(connection: sqlite3.Connection) -> list[dict]:
    rows = connection.execute("SELECT seq, ts, item_id, kind, data FROM events ORDER BY seq").fetchall()
    return [{"seq": r[0], "ts": r[1], "item_id": r[2], "kind": r[3], "data": json.loads(r[4] or "{}")}
            for r in rows]


def write_report(cwd: Path, root: Path, board_path: Path) -> None:
    con = sqlite3.connect(f"file:{board_path}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    events = load_events(con)
    items = {r["id"]: dict(r) for r in con.execute("SELECT id, status, attempts, max_attempts, depends_on FROM items")}
    lessons = [r[0] for r in con.execute("SELECT text FROM lessons ORDER BY seq")]
    journal_mode = con.execute("PRAGMA journal_mode").fetchone()[0]
    con.close()

    def evs(item: str, kind: str | None = None) -> list[dict]:
        return [e for e in events if e["item_id"] == item and (kind is None or e["kind"] == kind)]

    def kinds(item: str) -> list[str]:
        return [e["kind"] for e in evs(item)]

    def models(item: str) -> list[str | None]:
        return [e["data"].get("model") for e in evs(item, "dispatched")]

    def merged(item: str) -> list[list[str]]:
        return [e["data"].get("landed") or [] for e in evs(item, "merged")]

    checks: list[dict] = []

    def record(pattern: str, passed: bool, evidence: str) -> None:
        checks.append({"pattern": pattern, "passed": bool(passed), "evidence": evidence})

    crash = items.get("crash-resume", {})
    stale = root / ".mas" / "work" / "crash-resume-a1" / "artifacts" / "crash.txt"
    record("crash → lease expiry → resume", crash.get("status") == "done" and crash.get("attempts") == 2 and "lease_expired" in kinds("crash-resume"),
           f"status={crash.get('status')} attempts={crash.get('attempts')} events={kinds('crash-resume')}")
    record("fresh compartment after crash", stale.exists() and (root / "artifacts" / "crash.txt").read_text().strip() == "recovered-after-dead-lease",
           f"stale partial preserved={stale.exists()}; recovered artifact landed on main")

    gate_kinds = kinds("recover-gate-retry")
    gate_models = models("recover-gate-retry")
    record("gate distrusts worker + retry/backoff/escalation",
           gate_kinds.count("rejected") == 1 and "requeued" in gate_kinds and gate_models == ["fast-agent", "recovery-agent"] and items["recover-gate-retry"]["status"] == "done",
           f"models={gate_models}; events={gate_kinds}")

    crash_finishes = [e["data"] for e in evs("recover-worker-crash", "worker_finished")]
    record("worker process crash recovery", len(crash_finishes) == 2 and crash_finishes[0].get("ok") is False and items["recover-worker-crash"]["status"] == "done",
           f"worker claims={[x.get('ok') for x in crash_finishes]}; attempts={items['recover-worker-crash']['attempts']}")

    timeout_finishes = [e["data"] for e in evs("recover-timeout-recovery", "worker_finished")]
    record("stuck worker budget + retry", len(timeout_finishes) == 2 and "timeout" in str(timeout_finishes[0].get("error", "")).lower() and items["recover-timeout-recovery"]["status"] == "done",
           f"first error={timeout_finishes[0].get('error') if timeout_finishes else None}")

    heartbeat_finishes = [e["data"] for e in evs("recover-heartbeat-survival", "worker_finished")]
    heartbeat_seconds = float(heartbeat_finishes[-1].get("seconds") or 0) if heartbeat_finishes else 0
    record("heartbeats protect healthy long work", heartbeat_seconds >= 2.5 and "lease_expired" not in kinds("recover-heartbeat-survival"),
           f"worker ran {heartbeat_seconds:.1f}s on a 2s lease without expiry")

    permanent = items.get("recover-permanent-failure", {})
    record("circuit breaker + preserved evidence", permanent.get("status") == "parked" and permanent.get("attempts") == 2 and kinds("recover-permanent-failure").count("rejected") == 2,
           f"status={permanent.get('status')} attempts={permanent.get('attempts')} rejected={kinds('recover-permanent-failure').count('rejected')}")

    spawned = evs("plan-recovery", "spawned")
    record("dynamic spawning validates untrusted plans", bool(spawned) and "spawn_skipped" in kinds("plan-recovery") and len(spawned[-1]["data"].get("items") or []) == 12,
           f"spawned={len(spawned[-1]['data'].get('items') or []) if spawned else 0}; malformed entry skipped")

    report_item = items.get("recovery-report", {})
    report_deps = json.loads(report_item.get("depends_on") or "[]")
    terminal = all(v["status"] in ("done", "parked", "leased") for k, v in items.items() if k != "recovery-report")
    record("dependencies + settled policy + run-last", terminal and "recover-permanent-failure" in report_deps and report_item.get("status") == "leased",
           "report ran last after successful work was done and the irrecoverable dependency was parked")

    record("idempotent landing", items["recover-idempotent-second"]["status"] == "done" and [] in merged("recover-idempotent-second"),
           f"second merge landed={merged('recover-idempotent-second')} (empty means already identical)")
    record("scoped merge contains stray writes", (root / "artifacts" / "scoped.txt").exists() and not (root / "SHOULD_NOT_LAND.txt").exists(),
           "allowed artifact landed; undeclared SHOULD_NOT_LAND.txt stayed inside its disposable worktree")

    schema_verdicts = [e["data"] for e in evs("recover-schema-gate", "verified")]
    record("schema gate", bool(schema_verdicts) and schema_verdicts[-1].get("kind") == "schema",
           "structured manifest passed schema verification")
    record("command gate", any(e["data"].get("kind") == "cmd" for e in evs("recover-heartbeat-survival", "verified")),
           "artifact passed an independently executed command check")

    lesson_ok = (root / "artifacts" / "lesson-consumer.txt").read_text().strip() == "learned-cobalt-42"
    record("durable lesson/context transfer", lesson_ok and any("RECOVERY TOKEN: cobalt-42" in x for x in lessons),
           "dependent worker recovered cobalt-42 from the board's lesson memory")

    compartment_paths = [e["data"].get("path") for e in events if e["kind"] == "compartment"]
    record("one compartment per attempt", len(compartment_paths) == len(set(compartment_paths)) and len(compartment_paths) >= 17,
           f"{len(compartment_paths)} unique worktree paths for {len(compartment_paths)} attempts")

    claims = [(e["item_id"], e["data"].get("attempt")) for e in events if e["kind"] == "claimed"]
    record("atomic claims", len(claims) == len(set(claims)), f"{len(claims)} claims; no item-attempt claimed twice")
    record("append-only SQLite WAL event log", journal_mode.lower() == "wal" and [e["seq"] for e in events] == sorted(e["seq"] for e in events),
           f"journal_mode={journal_mode}; {len(events)} ordered events")

    worker_kinds = {e["data"].get("worker") for e in events if e["kind"] == "dispatched"}
    record("interchangeable mixed workers", {"chaos", "observer"}.issubset(worker_kinds), f"dispatched worker kinds={sorted(x for x in worker_kinds if x)}")

    report = {
        "passed": sum(1 for c in checks if c["passed"]),
        "total": len(checks),
        "checks": checks,
        "items": {k: {"status": v["status"], "attempts": v["attempts"], "max_attempts": v["max_attempts"]} for k, v in sorted(items.items())},
        "event_count_before_report_gate": len(events),
    }
    write(cwd, "result/recovery.json", json.dumps(report, indent=2) + "\n")
    by_pattern = {row["pattern"]: row for row in checks}
    nine_tools = [
        ("1", "Bounded contexts", "dynamic spawning validates untrusted plans"),
        ("2", "Bulkheads / isolation", "one compartment per attempt"),
        ("3", "Queue + competing consumers", "atomic claims"),
        ("4", "Idempotency + leases", "idempotent landing"),
        ("5", "Timeouts + retries + backoff", "stuck worker budget + retry"),
        ("6", "Circuit breaker", "circuit breaker + preserved evidence"),
        ("7", "Supervisor / restart from board", "crash → lease expiry → resume"),
        ("8", "Health checks + contracts", "gate distrusts worker + retry/backoff/escalation"),
        ("9", "Event sourcing + views", "append-only SQLite WAL event log"),
    ]
    lines = ["# Demo 6 · Recovery under intentional failure", "",
             f"**{report['passed']}/{report['total']} recovery patterns demonstrated.**", "",
             "## The nine tools from the lecture", "",
             "| tool | pattern | observed evidence |", "|---:|---|---|"]
    for number, name, pattern in nine_tools:
        evidence = by_pattern[pattern]["evidence"].replace("|", "\\|").replace("\n", " ")
        lines.append(f"| {number} | {name} | {evidence} |")
    lines += ["", "## Detailed executable checks", "",
             "| pattern | result | evidence |", "|---|---:|---|"]
    for row in checks:
        evidence = row["evidence"].replace("|", "\\|").replace("\n", " ")
        lines.append(f"| {row['pattern']} | {'✓' if row['passed'] else '✕'} | {evidence} |")
    lines += ["", "## Board observed by the run-last worker", "", "| item | status | attempts |", "|---|---|---:|"]
    for item_id, row in report["items"].items():
        lines.append(f"| `{item_id}` | {row['status']} | {row['attempts']}/{row['max_attempts']} |")
    lines += ["", "The parked item is intentional: recovery includes making failure bounded, preserving evidence, and allowing `deps=settled` work to continue.", ""]
    write(cwd, "result/recovery.md", "\n".join(lines))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cwd", required=True)
    parser.add_argument("--root", required=True)
    parser.add_argument("--board", required=True)
    parser.add_argument("--model", default="")
    parser.add_argument("--prompt-file", required=True)
    parser.add_argument("--python", required=True)
    parser.add_argument("--verifier", required=True)
    args = parser.parse_args(argv)
    cwd, root = Path(args.cwd), Path(args.root)
    item_id, attempt = identity(cwd)
    if item_id == "recover-lesson-source":
        # The orchestrator intentionally stores only the first summary line as a lesson.
        print("RECOVERY TOKEN: cobalt-42", flush=True)
    else:
        print(f"{item_id}: attempt {attempt} on {args.model or 'unversioned worker'}", flush=True)

    if item_id == "plan-recovery":
        write_plan(cwd, args.python, args.verifier)
        print("generated a recovery plan with one malformed entry", flush=True)
    elif item_id == "crash-resume":
        write(cwd, "artifacts/crash.txt", "recovered-after-dead-lease\n")
        print("recovered work in a fresh compartment", flush=True)
    elif item_id == "recover-heartbeat-survival":
        print("healthy worker is deliberately running longer than its lease", flush=True)
        time.sleep(3)
        write(cwd, "artifacts/heartbeat.txt", "heartbeat-kept-lease\n")
        print("completed while heartbeats renewed ownership", flush=True)
    elif item_id == "recover-gate-retry":
        write(cwd, "artifacts/gate-retry.txt", "confident-but-wrong\n" if attempt == 1 else "repaired-by-retry\n")
        print("I am certain this output is correct", flush=True)
    elif item_id == "recover-worker-crash":
        if attempt == 1:
            print("chaos-worker: simulated process crash", file=sys.stderr, flush=True)
            return 17
        write(cwd, "artifacts/worker-crash.txt", "recovered-after-process-exit\n")
        print("replacement worker completed", flush=True)
    elif item_id == "recover-timeout-recovery":
        if attempt == 1:
            print("simulating a stuck worker until the budget kills it", flush=True)
            time.sleep(10)
        write(cwd, "artifacts/timeout.txt", "recovered-after-timeout\n")
        print("retry completed within budget", flush=True)
    elif item_id in {"recover-idempotent-first", "recover-idempotent-second"}:
        write(cwd, "artifacts/idempotent.txt", "canonical-result\n")
        print("wrote the canonical result", flush=True)
    elif item_id == "recover-scoped-merge":
        write(cwd, "artifacts/scoped.txt", "allowed-result\n")
        write(cwd, "SHOULD_NOT_LAND.txt", "accidental out-of-scope write\n")
        print("produced one declared artifact and one stray file", flush=True)
    elif item_id == "recover-schema-gate":
        write(cwd, "artifacts/manifest.json", json.dumps({"status": "recovered", "generation": attempt}, indent=2) + "\n")
        print("produced structured recovery manifest", flush=True)
    elif item_id == "recover-lesson-source":
        write(cwd, "artifacts/lesson-source.txt", "lesson-published\n")
        print("published recovery lesson", flush=True)
    elif item_id == "recover-lesson-consumer":
        prompt = Path(args.prompt_file).read_text()
        value = "learned-cobalt-42\n" if "RECOVERY TOKEN: cobalt-42" in prompt else "lesson-missing\n"
        write(cwd, "artifacts/lesson-consumer.txt", value)
        print("used durable lesson context", flush=True)
    elif item_id == "recover-permanent-failure":
        write(cwd, "artifacts/permanent.txt", f"still-broken-attempt-{attempt}\n")
        print("claiming success even though this fault is permanent", flush=True)
    elif item_id == "recovery-report":
        write_report(cwd, root, Path(args.board))
        print("assembled the recovery report directly from SQLite evidence", flush=True)
    else:
        print(f"unknown demo item {item_id}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
