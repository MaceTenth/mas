"""Round 4: knowledge-transfer topologies on the XL target.

- stigmergy: parallel swarm + shared hints board (read before, post after).
  Knowledge flows through the ENVIRONMENT (append-only board).
- chain: 40 agents strictly in sequence on one shared tree; each agent's
  done-summary becomes the next agent's handoff note. Knowledge flows
  HOP-BY-HOP (the telephone game). No gates, no retries — pure chain.

Baselines for comparison (already measured, same task/model/tools):
  single agent 70 turns / 190.8s / $0.36 ; isolated swarm 350 turns / 130.2s / $1.31.
"""
import concurrent.futures as cf
import json
import subprocess
import sys
import threading
import time
from pathlib import Path

from orchestrator2 import (PYTHON, GH_REPO, PRICE, RUNS, gh, fresh_copy,
                           score, cost, brief_for, module_of)
from worker2 import Worker

WORKER_TURNS = 10
CONCURRENCY = 12

STIG_PREFIX = """You are one of 40 agents working in parallel, each on a different GitHub issue in this repository. There is a shared hints board: agents post findings there as they finish. FIRST call read_hints — a sibling agent may already have discovered something that saves you work. After your module's tests pass, call post_hint ONCE with the most transferable insight from your fix (max 2 sentences), then call done.

"""

def chain_brief(idx, total, note, issue):
    return (f"You are agent #{idx} of {total} in a RELAY. Agents before you fixed "
            f"earlier issues in this same repository; agents after you will fix later ones. "
            f"Handoff note from the previous agent:\n\"\"\"\n{note}\n\"\"\"\n\n"
            f"Your assignment is ONLY the issue below. When your module's tests pass, "
            f"call done — your summary will be handed VERBATIM to the next agent, so "
            f"include whatever you learned that transfers (bug patterns, where to look, "
            f"how to fix fast).\n\n{brief_for(issue)}")


def fetch_all_issues():
    out = gh("issue", "list", "-R", GH_REPO, "--state", "all",
             "--json", "number,title,body", "--limit", "100")
    issues = [i for i in json.loads(out) if "__pycache__" not in i["title"]]
    issues.sort(key=lambda i: i["number"])
    return issues


def run_stigmergy(issues):
    final_repo = fresh_copy("stig")
    hints_path = RUNS / "stig" / "HINTS.md"
    hints_lock = threading.Lock()
    t0 = time.monotonic()

    def handle(issue):
        module = module_of(issue)
        repo = fresh_copy(f"stig_w_{module}")
        w = Worker(repo, PYTHON, label=module,
                   hints_path=hints_path, hints_lock=hints_lock)
        res = w.run(STIG_PREFIX + brief_for(issue), max_turns=WORKER_TURNS)
        verdict = score(repo, f"tests/test_{module}.py")
        finished_at = round(time.monotonic() - t0, 1)
        closed = False
        if verdict["failed"] == 0 and verdict["passed"] > 0:
            import shutil
            shutil.copy(repo / "src" / f"{module}.py", final_repo / "src" / f"{module}.py")
            gh("issue", "close", str(issue["number"]), "-R", GH_REPO,
               "-c", f"Fixed by stigmergic worker: {verdict['passed']} tests pass "
                     f"({res['turns']} turns; read {w.hints_read} hint boards, posted {w.hints_posted}).")
            closed = True
        print(f"[stig] {module}: t={finished_at}s turns={res['turns']} "
              f"read={w.hints_read} posted={w.hints_posted} closed={closed}", flush=True)
        return {"module": module, "issue": issue["number"], "turns": res["turns"],
                "seconds": res["seconds"], "finished_at": finished_at,
                "hints_read": w.hints_read, "hints_posted": w.hints_posted,
                "verified": verdict, "closed": closed, "usage": res["usage"]}

    with cf.ThreadPoolExecutor(max_workers=CONCURRENCY) as ex:
        results = list(ex.map(handle, issues))

    wall = round(time.monotonic() - t0, 1)
    final = score(final_repo)
    usage = {k: sum(r["usage"][k] for r in results) for k in PRICE}
    ordered = sorted(results, key=lambda r: r["finished_at"])
    curve = [{"order": n + 1, "module": r["module"], "turns": r["turns"],
              "finished_at": r["finished_at"]} for n, r in enumerate(ordered)]
    return {
        "condition": "stigmergic_swarm",
        "wall_seconds": wall,
        "final_suite": final,
        "issues_closed": sum(1 for r in results if r["closed"]),
        "turns_used": sum(r["turns"] for r in results),
        "hints_posted": sum(r["hints_posted"] for r in results),
        "hints_read_calls": sum(r["hints_read"] for r in results),
        "usage": usage,
        "est_cost_usd": cost(usage),
        "learning_curve": curve,
        "hints_board": hints_path.read_text() if hints_path.exists() else "",
    }


def run_chain(issues):
    repo = fresh_copy("chain")
    t0 = time.monotonic()
    usage = {k: 0 for k in PRICE}
    note = "(none - you are the first agent in the relay)"
    stages = []
    for idx, issue in enumerate(issues, 1):
        module = module_of(issue)
        w = Worker(repo, PYTHON, label=f"chain#{idx}:{module}")
        res = w.run(chain_brief(idx, len(issues), note, issue), max_turns=WORKER_TURNS)
        for k in PRICE:
            usage[k] += res["usage"][k]
        verdict = score(repo, f"tests/test_{module}.py")
        fixed = verdict["failed"] == 0 and verdict["passed"] > 0
        note = (res["done_summary"] or "").strip()[:1500] or "(previous agent left no note)"
        stages.append({"stage": idx, "module": module, "turns": res["turns"],
                       "seconds": res["seconds"], "fixed": fixed,
                       "note_chars": len(note)})
        print(f"[chain] #{idx} {module}: turns={res['turns']} fixed={fixed} "
              f"note={len(note)}ch", flush=True)
    wall = round(time.monotonic() - t0, 1)
    final = score(repo)
    return {
        "condition": "agent_chain",
        "wall_seconds": wall,
        "final_suite": final,
        "modules_fixed": sum(1 for s in stages if s["fixed"]),
        "turns_used": sum(s["turns"] for s in stages),
        "usage": usage,
        "est_cost_usd": cost(usage),
        "stages": stages,
    }


if __name__ == "__main__":
    mode = sys.argv[1]  # stigmergy | chain
    issues = fetch_all_issues()
    print(f"{len(issues)} issues loaded from {GH_REPO}", flush=True)
    result = run_stigmergy(issues) if mode == "stigmergy" else run_chain(issues)
    out = RUNS / f"result_{mode}.json"
    out.write_text(json.dumps(result, indent=2))
    print(json.dumps({k: v for k, v in result.items()
                      if k not in ("learning_curve", "stages", "hints_board")},
                     indent=2), flush=True)
    print(f"written: {out}", flush=True)
