"""Round 3: fault-injection (chaos) benchmark on the XL target.

Failure model, identical for both conditions:
- every API turn has CHAOS_RATE probability of killing the agent
- a kill destroys context only; the working tree (disk) survives
- the orchestrator auto-restarts: a fresh agent, fresh context, same tree

Metric: wall-clock, turns, and cost to reach a fully green suite despite
kills — resilience measured as time-and-cost-to-completion.
Safety caps only (no fairness budget cliff): per-issue attempts and a global
turn ceiling far above expected need.
"""
import concurrent.futures as cf
import json
import random
import sys
import time
from pathlib import Path

from orchestrator2 import (BENCH, PYTHON, GH_REPO, PRICE, RUNS, gh,
                           fetch_issues, fresh_copy, score, cost, brief_for,
                           module_of)
from worker2 import Worker

CHAOS_RATE = 0.05
SEED = 7
CONCURRENCY = 12
WORKER_TURNS = 10          # per attempt
MAX_ATTEMPTS = 6           # per issue / per single-agent restart chain step
GLOBAL_TURN_CAP = 1000


def merge_usage(total, u):
    for k in PRICE:
        total[k] += u[k]


def run_multi(issues):
    final_repo = fresh_copy("chaos_multi")
    t0 = time.monotonic()
    usage = {k: 0 for k in PRICE}

    def handle(issue):
        module = module_of(issue)
        repo = fresh_copy(f"chaos_w_{module}")   # survives kills, like real disk
        kills = 0
        attempts = 0
        turns = 0
        closed = False
        verdict = None
        while attempts < MAX_ATTEMPTS:
            attempts += 1
            rng = random.Random(SEED * 10007 + hash(module) % 100000 + attempts)
            w = Worker(repo, PYTHON, label=f"worker:{module}#{attempts}")
            res = w.run(brief_for(issue), max_turns=WORKER_TURNS,
                        chaos_rate=CHAOS_RATE, rng=rng)
            turns += res["turns"]
            merge_usage(usage, res["usage"])
            if res["killed"]:
                kills += 1
                continue                          # re-dispatch on same tree
            verdict = score(repo, f"tests/test_{module}.py")
            if verdict["failed"] == 0 and verdict["passed"] > 0:
                import shutil
                shutil.copy(repo / "src" / f"{module}.py",
                            final_repo / "src" / f"{module}.py")
                gh("issue", "close", str(issue["number"]), "-R", GH_REPO,
                   "-c", f"Fixed under chaos: {verdict['passed']} tests pass "
                         f"({attempts} attempt(s), {kills} kill(s) survived, {turns} turns).")
                closed = True
                break
        print(f"[chaos-multi] {module}: closed={closed} attempts={attempts} "
              f"kills={kills} turns={turns}", flush=True)
        return {"module": module, "issue": issue["number"], "attempts": attempts,
                "kills": kills, "turns": turns, "closed": closed, "verified": verdict}

    with cf.ThreadPoolExecutor(max_workers=CONCURRENCY) as ex:
        results = list(ex.map(handle, issues))

    wall = round(time.monotonic() - t0, 1)
    final = score(final_repo)
    return {
        "condition": "chaos_multi",
        "chaos_rate": CHAOS_RATE,
        "wall_seconds": wall,
        "final_suite": final,
        "completed": final["failed"] == 0,
        "issues_closed": sum(1 for r in results if r["closed"]),
        "kills_survived": sum(r["kills"] for r in results),
        "restarts": sum(r["attempts"] - 1 for r in results),
        "turns_used": sum(r["turns"] for r in results),
        "usage": usage,
        "est_cost_usd": cost(usage),
        "per_worker": results,
    }


def run_single(issues):
    repo = fresh_copy("chaos_single")
    t0 = time.monotonic()
    usage = {k: 0 for k in PRICE}
    combined = "\n\n---\n\n".join(brief_for(i) for i in issues)
    brief = (
        f"This repository has {len(issues)} open GitHub issues, all listed below. "
        f"Fix ALL of them so the entire test suite passes. Note: previous work "
        f"may already be present in the tree — run the test suite first to see "
        f"what is still failing.\n\n{combined}"
    )
    kills = 0
    restarts = 0
    turns = 0
    rng = random.Random(SEED)
    completed = False
    while turns < GLOBAL_TURN_CAP:
        w = Worker(repo, PYTHON, label=f"single#{restarts + 1}")
        res = w.run(brief, max_turns=GLOBAL_TURN_CAP - turns,
                    chaos_rate=CHAOS_RATE, rng=rng)
        turns += res["turns"]
        merge_usage(usage, res["usage"])
        if res["killed"]:
            kills += 1
            restarts += 1
            print(f"[chaos-single] restart #{restarts} after kill at cumulative "
                  f"turn {turns}", flush=True)
            continue
        # agent stopped voluntarily — verify; if suite is red, re-dispatch
        verdict = score(repo)
        if verdict["failed"] == 0:
            completed = True
            break
        restarts += 1
        print(f"[chaos-single] declared done but suite red ({verdict}), "
              f"re-dispatching (restart #{restarts})", flush=True)
        if restarts >= MAX_ATTEMPTS * 4:
            break

    wall = round(time.monotonic() - t0, 1)
    final = score(repo)
    return {
        "condition": "chaos_single",
        "chaos_rate": CHAOS_RATE,
        "wall_seconds": wall,
        "final_suite": final,
        "completed": final["failed"] == 0 and completed,
        "kills_survived": kills,
        "restarts": restarts,
        "turns_used": turns,
        "usage": usage,
        "est_cost_usd": cost(usage),
    }


if __name__ == "__main__":
    mode = sys.argv[1]
    issues = fetch_issues()
    if not issues:
        print("no open issues found — aborting")
        sys.exit(1)
    print(f"fetched {len(issues)} open issues from {GH_REPO} "
          f"(chaos={CHAOS_RATE}, seed={SEED})", flush=True)
    result = run_multi(issues) if mode == "multi" else run_single(issues)
    out = RUNS / f"result_{mode}_chaos.json"
    out.write_text(json.dumps(result, indent=2))
    print(json.dumps({k: v for k, v in result.items() if k != "per_worker"},
                     indent=2), flush=True)
    print(f"written: {out}", flush=True)
