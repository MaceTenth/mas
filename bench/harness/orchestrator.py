"""Benchmark orchestrator: swarm-with-GitHub-Issues vs single agent.

Fairness contract:
- Same model, same system prompt, same tools, same repo snapshot.
- The single agent receives the UNION of all issue briefs (identical info).
- Turn budgets are equal in aggregate: N workers x T turns == 1 agent x N*T turns.
- Scoring is done by the orchestrator running pytest on the final tree —
  never by agent self-report.
"""
import concurrent.futures as cf
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

from worker import Worker

BENCH = Path(__file__).resolve().parent.parent
TARGET = BENCH / "target"
RUNS = BENCH / "runs"
PYTHON = str(BENCH.parent / ".venv" / "bin" / "python")
GH_REPO = "MaceTenth/claude-mas-bench"

WORKER_TURNS = 14
CONCURRENCY = 8

# Haiku 4.5 pricing, USD per million tokens
PRICE = {"input": 1.00, "output": 5.00, "cache_read": 0.10, "cache_write": 1.25}


def gh(*args):
    r = subprocess.run(["gh", *args], capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        print(f"[gh] WARNING: gh {' '.join(args[:3])}... failed: {r.stderr.strip()[:200]}")
    return r.stdout


def fetch_issues():
    out = gh("issue", "list", "-R", GH_REPO, "--state", "open",
             "--json", "number,title,body", "--limit", "50")
    issues = json.loads(out)
    issues.sort(key=lambda i: i["number"])
    return issues


def fresh_copy(name):
    dst = RUNS / name / "repo"
    if dst.parent.exists():
        shutil.rmtree(dst.parent)
    dst.parent.mkdir(parents=True)
    shutil.copytree(TARGET, dst, ignore=shutil.ignore_patterns(".git", "__pycache__", ".pytest_cache"))
    return dst


def score(repo_dir, test_path=None):
    cmd = [PYTHON, "-m", "pytest", "-q", "--no-header"]
    if test_path:
        cmd.append(test_path)
    r = subprocess.run(cmd, cwd=repo_dir, capture_output=True, text=True, timeout=120)
    out = r.stdout + r.stderr
    passed = sum(int(n) for n in re.findall(r"(\d+) passed", out))
    failed = sum(int(n) for n in re.findall(r"(\d+) failed", out))
    errors = sum(int(n) for n in re.findall(r"(\d+) error", out))
    return {"passed": passed, "failed": failed + errors}


def cost(usage):
    return round(sum(usage[k] / 1e6 * PRICE[k] for k in PRICE), 4)


def brief_for(issue):
    return f"GitHub issue #{issue['number']}: {issue['title']}\n\n{issue['body']}"


def run_multi(issues):
    # merged tree that verified fixes land in (the "main branch")
    final_repo = fresh_copy("multi")
    t0 = time.monotonic()
    results = []

    def handle(issue):
        m = re.search(r"src/(\w+)\.py", issue["title"])
        module = m.group(1) if m else f"issue{issue['number']}"
        # isolated working copy per worker (the git-worktree pattern)
        repo = fresh_copy(f"multi_w_{module}")
        w = Worker(repo, PYTHON, label=f"worker:{module}")
        res = w.run(brief_for(issue), max_turns=WORKER_TURNS)
        # orchestrator-side verification (never trust self-report)
        verdict = score(repo, f"tests/test_{module}.py")
        if verdict["failed"] == 0 and verdict["passed"] > 0:
            # merge: only the worker's own module lands on main
            shutil.copy(repo / "src" / f"{module}.py",
                        final_repo / "src" / f"{module}.py")
        res["issue"] = issue["number"]
        res["module"] = module
        res["verified"] = verdict
        if verdict["failed"] == 0 and verdict["passed"] > 0:
            gh("issue", "close", str(issue["number"]), "-R", GH_REPO,
               "-c", f"Fixed by worker agent: {verdict['passed']} tests pass "
                     f"({res['turns']} turns, {res['seconds']}s).")
            res["closed"] = True
        else:
            gh("issue", "comment", str(issue["number"]), "-R", GH_REPO,
               "-b", f"Worker finished but verification failed: {verdict}. Issue stays open.")
            res["closed"] = False
        print(f"[multi] {module}: verified={verdict} turns={res['turns']} {res['seconds']}s")
        return res

    with cf.ThreadPoolExecutor(max_workers=CONCURRENCY) as ex:
        results = list(ex.map(handle, issues))

    wall = round(time.monotonic() - t0, 1)
    final = score(final_repo)
    usage = {k: sum(r["usage"][k] for r in results) for k in PRICE}
    return {
        "condition": "multi_agent_gh_issues",
        "wall_seconds": wall,
        "final_suite": final,
        "issues_closed": sum(1 for r in results if r["closed"]),
        "usage": usage,
        "est_cost_usd": cost(usage),
        "agents": len(results),
        "aggregate_turn_budget": WORKER_TURNS * len(results),
        "turns_used": sum(r["turns"] for r in results),
        "per_worker": [
            {k: r[k] for k in ("module", "issue", "turns", "seconds", "verified", "closed")}
            for r in results
        ],
    }


def run_single(issues):
    repo = fresh_copy("single")
    t0 = time.monotonic()
    combined = "\n\n---\n\n".join(brief_for(i) for i in issues)
    brief = (
        f"This repository has {len(issues)} open GitHub issues, all listed below. "
        f"Fix ALL of them so the entire test suite passes.\n\n{combined}"
    )
    w = Worker(repo, PYTHON, label="single")
    res = w.run(brief, max_turns=WORKER_TURNS * len(issues))
    wall = round(time.monotonic() - t0, 1)
    final = score(repo)
    per_module = {}
    for i in issues:
        m = re.search(r"src/(\w+)\.py", i["title"])
        module = m.group(1)
        per_module[module] = score(repo, f"tests/test_{module}.py")
    return {
        "condition": "single_agent",
        "wall_seconds": wall,
        "final_suite": final,
        "modules_fully_fixed": sum(1 for v in per_module.values()
                                   if v["failed"] == 0 and v["passed"] > 0),
        "usage": res["usage"],
        "est_cost_usd": cost(res["usage"]),
        "agents": 1,
        "aggregate_turn_budget": WORKER_TURNS * len(issues),
        "turns_used": res["turns"],
        "declared_done": res["done_summary"] is not None,
        "per_module": per_module,
    }


if __name__ == "__main__":
    mode = sys.argv[1]  # "multi" | "single"
    issues = fetch_issues()
    if not issues:
        # issues may already be closed from a prior run; reopen for fairness
        print("no open issues found — aborting")
        sys.exit(1)
    print(f"fetched {len(issues)} open issues from {GH_REPO}")
    result = run_multi(issues) if mode == "multi" else run_single(issues)
    out = RUNS / f"result_{mode}.json"
    out.write_text(json.dumps(result, indent=2))
    print(json.dumps({k: v for k, v in result.items()
                      if k not in ("per_worker", "per_module")}, indent=2))
    print(f"written: {out}")
