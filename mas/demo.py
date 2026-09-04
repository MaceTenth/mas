"""`mas demo` — self-contained demonstrations on a small Python library with
8 modules, each containing one planted bug and a definitive test file. Eight
independent, verifiable items — the shape a swarm is for.

  demo 1  one fleet:    4 Claude workers, verify-then-land           (mas demo run 1)
  demo 2  mixed fleet:  Claude and Codex on the same repo/board/gate (mas demo run 2)
  demo 3  debate or vote: no tests, no oracle — 8 independent reviewers vote on a PR,
          one adjudicator debates the votes, a script tallies both       (mas demo run 3)
  demo 4  many eyes: a harder PR with four planted bugs across four files — does the
          union of independent reviewers beat any single one?           (mas demo run 4)

Every flag a demo needs is written into the project's .mas/config.json, so a
plain `mas run` inside the demo directory does the right thing.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

from .board import SQLiteBoard, Item


HERE = Path(__file__).parent
TARGET = HERE / "demo_target"
VOTE_TARGET = HERE / "demo_vote" / "target"
TALLY = HERE / "demo_vote" / "tally.py"
REVIEW_TARGET = HERE / "demo_review" / "target"
REVIEW_TALLY = HERE / "demo_review" / "tally.py"
DEFAULT_FLEET = ["claude", "codex"]


def _reviewers(fleet: list[str] | None, n: int = 8):
    """(id, kind, pinned model) for n reviewers. A single-kind fleet alternates models so the
    'views' still differ; a mixed fleet alternates harnesses."""
    fleet = [k for k in (fleet or DEFAULT_FLEET) if k] or DEFAULT_FLEET
    out = []
    for i in range(1, n + 1):
        kind = fleet[(i - 1) % len(fleet)]
        model = None
        if len(set(fleet)) == 1 and kind == "claude":
            model = ["haiku", "sonnet"][(i - 1) % 2]
        vid = f"vote-{i}-{kind}" + (f"-{model}" if model else "")
        out.append((vid, kind, model))
    return out

PERSONAS = ["a skeptical maintainer who has been burned by caches before",
            "a security auditor looking for data exposure",
            "a QA engineer who thinks in concrete call sequences",
            "a new team member reading this code for the first time"]
VOTE_SCHEMA = {"required": ["bug", "severity", "location", "scenario", "fix", "confidence"],
               "properties": {"bug": {"type": "boolean"}, "severity": {"type": "string"}, "location": {"type": "string"},
                              "scenario": {"type": "string"}, "fix": {"type": "string"}, "confidence": {"type": "number"}}}
FINAL_SCHEMA = {"required": ["bug", "severity", "location", "scenario", "fix", "agreed_with", "overruled", "reasoning"],
                "properties": {"bug": {"type": "boolean"}, "location": {"type": "string"}, "agreed_with": {"type": "array"},
                               "overruled": {"type": "array"}, "reasoning": {"type": "string"}}}


def build_vote_items(board: SQLiteBoard, cfg: dict, py: str, fleet: list[str] | None = None, **_) -> list[Item]:
    """8 independent votes (4 claude · 4 codex · 4 personas) → 1 debate → 1 deterministic tally."""
    items, vote_ids = [], []
    for i, (vid, kind, model) in enumerate(_reviewers(fleet), 1):
        persona = PERSONAS[(i - 1) // 2 % len(PERSONAS)]
        vote_ids.append(vid)
        it = Item(id=vid, title=f"Review PR #142 as {persona.split(' who')[0].split(' looking')[0].split(' reading')[0]}",
                  brief=(f"You are ONE of several independent reviewers of PR #142 (read PR.md, then svc/profile_cache.py). "
                         f"You do not see the other reviews. Review it as {persona}.\n\n"
                         "QUESTION: does this change introduce a bug that would affect production — a correctness or security "
                         "problem, not style? If there are several issues, report the most serious one.\n\n"
                         f"Write your verdict to votes/{vid}.json — a single JSON object exactly of this shape:\n"
                         '{"bug": true or false, "severity": "none|low|medium|high|critical", "location": "<function and line, a few words>", '
                         '"scenario": "<one concrete failing call sequence, or none>", "fix": "<one sentence>", "confidence": <0.0-1.0>}\n\n'
                         "RULES: create only that one file; do not modify svc/ or PR.md; do not write tests. Decide by reading — you may "
                         "run python to confirm a scenario. Keep every field short (the whole file under 120 words)."),
                  check=f"schema:votes/{vid}.json", merge_paths=[f"votes/{vid}.json"], priority=10,
                  worker_pref=kind, max_attempts=int(cfg.get("max_attempts", 3)),
                  meta={"schema": VOTE_SCHEMA, **({"model": model} if model else {})})
        board.add(it); items.append(it)
    debate = Item(id="debate", title="Adjudicate the 8 reviews (debate)",
                  brief=("You are the adjudicator. In votes/ are the independent reviews of PR #142 that have landed so far, by "
                         "different reviewers using two different coding harnesses (see the file names). Some reviewers may have "
                         "failed; adjudicate whatever is present RIGHT NOW — never wait for, poll for, or go looking for missing "
                         "reviews (not in git branches, not anywhere). Read PR.md and svc/profile_cache.py yourself, then read every "
                         "votes/*.json. Where reviewers disagree, decide who is right from the code, not from the head count.\n\n"
                         "Write final.json — one JSON object exactly of this shape:\n"
                         '{"bug": true or false, "severity": "...", "location": "<function and line>", "scenario": "<one concrete failing call sequence>", '
                         '"fix": "<one sentence>", "agreed_with": ["vote-…", …], "overruled": ["vote-…", …], "reasoning": "<under 80 words>"}\n\n'
                         "RULES: create only final.json; do not modify anything else; do not write tests."),
                  check="schema:final.json", merge_paths=["final.json"], priority=5, worker_pref="claude",
                  depends_on=list(vote_ids), max_attempts=int(cfg.get("max_attempts", 3)),
                  meta={"schema": FINAL_SCHEMA, "model": "sonnet", "deps": "settled"})
    board.add(debate); items.append(debate)
    tally = Item(id="tally", title="Tally: majority vote vs debate vs the planted truth (deterministic)",
                 brief="Deterministic script — no model. Counts votes/*.json and final.json against the planted truth and writes result/summary.md.",
                 check="cmd:test -s result/summary.md && test -s result/tally.json", merge_paths=["result/summary.md", "result/tally.json"],
                 priority=1, worker_pref="tally", depends_on=list(vote_ids) + ["debate"], max_attempts=2, meta={"deps": "settled"})
    board.add(tally); items.append(tally)
    return items


def vote_config(py: str, fleet: list[str] | None = None, **_) -> dict:
    fleet = list(dict.fromkeys(fleet or DEFAULT_FLEET))
    return {"workers": fleet + ["tally"], "concurrency": 4, "lease_seconds": 120,
            "codex_overrides": ["model_reasoning_effort=\"medium\"", "mcp_servers={}"],
            "models": {"claude": ["haiku", "sonnet"], "codex": [None], "tally": [None]},
            "harnesses": {"tally": {"cmd": [py, str(TALLY), "{cwd}"], "prompt_via": "file", "summary": "stdout_tail", "activity": "lines"}}}


# ---------------------------------------------------------------- demo 4 · many eyes
FINDINGS_SCHEMA = {"required": ["findings", "confidence"],
                   "properties": {"findings": {"type": "array"}, "confidence": {"type": "number"}}}
CONSOLIDATED_SCHEMA = {"required": ["findings", "dropped", "reasoning"],
                       "properties": {"findings": {"type": "array"}, "dropped": {"type": "array"}, "reasoning": {"type": "string"}}}
FINDING_SHAPE = ('{"title": "<5-10 words>", "location": "<file, function, line>", "severity": "low|medium|high|critical", '
                 '"scenario": "<one concrete failing call sequence>", "fix": "<one sentence>"}')


def build_review_items(board: SQLiteBoard, cfg: dict, py: str, fleet: list[str] | None = None, **_) -> list[Item]:
    """8 independent reviews of a 5-file PR with several planted bugs → 1 consolidation → 1 tally."""
    items, ids = [], []
    for i, (vid, kind, model) in enumerate(_reviewers(fleet), 1):
        persona = PERSONAS[(i - 1) // 2 % len(PERSONAS)]
        ids.append(vid)
        it = Item(id=vid, title=f"Review PR #207 as {persona.split(' who')[0].split(' looking')[0].split(' reading')[0]}",
                  brief=(f"You are ONE of several independent reviewers of PR #207 (read PR.md, then every file under svc/). "
                         f"You do not see the other reviews. Review it as {persona}.\n\n"
                         "QUESTION: list EVERY bug in this change that would affect production — correctness, money, or security. "
                         "Ignore style, naming, and missing tests. Be concrete: a finding without a failing scenario is a guess.\n\n"
                         f"Write votes/{vid}.json — one JSON object exactly of this shape:\n"
                         '{"findings": [' + FINDING_SHAPE + ', ...], "confidence": <0.0-1.0>}\n'
                         "Up to 6 findings, most serious first; an empty list is a valid answer if you find nothing.\n\n"
                         "RULES: create only that one file; do not modify svc/ or PR.md; do not write tests. Decide by reading — you may "
                         "run python to confirm a scenario (e.g. compute a total, replay a call). Keep each field short."),
                  check=f"schema:votes/{vid}.json", merge_paths=[f"votes/{vid}.json"], priority=10,
                  worker_pref=kind, max_attempts=int(cfg.get("max_attempts", 3)),
                  meta={"schema": FINDINGS_SCHEMA, **({"model": model} if model else {})})
        board.add(it); items.append(it)
    debate = Item(id="debate", title="Consolidate the reviews (debate)",
                  brief=("You are the adjudicator. In votes/ are the independent reviews of PR #207 that have landed so far, from "
                         "different reviewers and harnesses (see the file names). Some reviewers may have failed; consolidate whatever "
                         "is present RIGHT NOW — never wait for, poll for, or go looking for missing reviews (not in git, not anywhere).\n\n"
                         "Read PR.md and every file under svc/ yourself, then every votes/*.json. Merge duplicate findings, keep every "
                         "real production bug, and DROP findings that are not real or not production-affecting — check each against the "
                         "code, not the head count. Where reviewers disagree, decide from the code.\n\n"
                         "Write final.json — one JSON object exactly of this shape:\n"
                         '{"findings": [' + FINDING_SHAPE + ', ...], "dropped": [{"title": "...", "why": "..."}, ...], "reasoning": "<under 100 words>"}\n\n'
                         "RULES: create only final.json; do not modify anything else; do not write tests."),
                  check="schema:final.json", merge_paths=["final.json"], priority=5, worker_pref="claude",
                  depends_on=list(ids), max_attempts=int(cfg.get("max_attempts", 3)),
                  meta={"schema": CONSOLIDATED_SCHEMA, "model": "sonnet", "deps": "settled"})
    board.add(debate); items.append(debate)
    tally = Item(id="tally", title="Tally: one reviewer vs majority vs union vs debate, against the planted bugs",
                 brief="Deterministic script — no model. Attributes every finding to a planted bug (or none) and writes result/summary.md.",
                 check="cmd:test -s result/summary.md && test -s result/tally.json", merge_paths=["result/summary.md", "result/tally.json"],
                 priority=1, worker_pref="tally", depends_on=list(ids) + ["debate"], max_attempts=2, meta={"deps": "settled"})
    board.add(tally); items.append(tally)
    return items


def review_config(py: str, fleet: list[str] | None = None, **_) -> dict:
    cfg = vote_config(py, fleet)
    cfg.update({"lease_seconds": 240, "max_turns": 30,
                "harnesses": {"tally": {"cmd": [py, str(REVIEW_TALLY), "{cwd}"], "prompt_via": "file", "summary": "stdout_tail", "activity": "lines"}}})
    return cfg

DEMOS = {
    "1": {
        "name": "demo 1 · one fleet",
        "tagline": "8 independent items · 4 Claude workers (haiku → sonnet on retry) · the gate re-runs every test file · only verified files land",
        "show": "board, leases with heartbeats, per-attempt worktrees, gate verdicts, idempotent landing, event log — Ctrl-C then `mas run` again to show resume",
        "config": {"workers": ["claude"], "concurrency": 4, "lease_seconds": 60},
        "assign": None,
    },
    "2": {
        "name": "demo 2 · mixed fleet",
        "tagline": "Claude and Codex working the SAME repo: one board, one gate, one main — 4 items each, verdicts and commits side by side",
        "show": "worker column alternates claude/codex, both stream tool calls, both are gated identically, `git log` shows commits from both; `mas dashboard` → done by worker",
        "config": {"workers": ["claude", "codex"], "concurrency": 4, "lease_seconds": 90,
                   "codex_overrides": ["model_reasoning_effort=\"medium\"", "mcp_servers={}"]},
        "assign": ["claude", "codex"],          # worker_pref by item index, round-robin
    },
    "3": {
        "name": "demo 3 · debate or vote",
        "tagline": "No tests, no oracle. 8 independent reviewers (4 Claude · 4 Codex · 4 personas) each vote on a PR with a planted bug; one adjudicator debates all 8; a deterministic tally scores vote vs debate vs a single sample",
        "show": "bulkheads (reviewers share nothing), schema gate (structure only — words can't be gated), depends_on (debate and tally wait for the votes to settle), a script as a worker (tally), result/summary.md at the end. Lesson from the first run: a brief that promised '8 reviews' when 4 had landed made the adjudicator spend its whole turn budget waiting for the missing ones — the brief is part of the contract",
        "config": vote_config,                  # callable(py, fleet): needs the python path for the tally harness
        "target": VOTE_TARGET,
        "commit": "demo: profile-service with PR #142 under review",
        "build": build_vote_items,
    },
    "4": {
        "name": "demo 4 · many eyes",
        "tagline": "A harder PR: five files, four planted bugs of different kinds (webhook replay, missing authorization, cents truncation, swallowed charge failure) and red herrings. 8 independent reviewers list every bug they see; one adjudicator consolidates; the tally scores one reviewer vs majority vs union vs debate",
        "show": "recall per reviewer vs union — the case for multiple views; unmatched findings — the precision cost; by-harness/by-model recall; the adjudicator as the precision step. `--fleet claude` runs it on haiku/sonnet alternating when Codex is unavailable",
        "config": review_config,
        "target": REVIEW_TARGET,
        "commit": "demo: billing-service with PR #207 under review",
        "build": build_review_items,
    },
}

BRIEFS = {
    "slugify": "URL slugs: consecutive punctuation must collapse to one hyphen, no leading/trailing hyphens, truncation must not leave a trailing hyphen.",
    "intervals": "Merge overlapping or touching (start,end) intervals from unsorted input; return sorted tuples.",
    "lru": "LRU cache: get() must refresh recency; put() must evict the LEAST recently used entry.",
    "csvlite": "CSV line parser: inside a quoted field a doubled quote \"\" is an escaped literal quote.",
    "pagination": "total_pages must round up; page_bounds must clamp the last page to total_items.",
    "roman": "int_to_roman must use subtractive forms (IV, IX, XL, XC, CD, CM).",
    "ratelimit": "Sliding window limiter: allow at most `limit` events per window — the (limit+1)th must be rejected.",
    "search": "find_insert_pos must return the LEFTMOST insertion index (like bisect_left); contains() depends on it.",
}


def init_demo(dest: Path, python: str | None = None, force: bool = False, demo: str = "1",
              base_config: dict | None = None, fleet: list[str] | None = None, **opts) -> tuple[Path, list[Item]]:
    spec = DEMOS.get(str(demo))
    if spec is None:
        raise SystemExit(f"unknown demo {demo!r} — see `mas demo list`")
    dest = dest.resolve()
    if dest.exists() and any(dest.iterdir()):
        if not force:
            raise SystemExit(f"{dest} is not empty — choose a new directory, or `mas demo init {dest} --force` to reset a previous demo")
        if not (dest / ".mas").is_dir():
            raise SystemExit(f"{dest} is not a mas project (no .mas/) — refusing to wipe it even with --force")
        shutil.rmtree(dest)
    if spec.get("generate"):
        hidden = Path(opts.get("hidden") or dest / ".mas" / "hidden")
        opts["hidden"] = hidden
        spec["generate"](dest, hidden, seed=int(opts.get("seed") or 7), n=int(opts.get("n") or 32))
    else:
        shutil.copytree(spec.get("target", TARGET), dest, ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache", ".git"))
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=dest, check=True)
    subprocess.run(["git", "add", "-A"], cwd=dest, check=True)
    subprocess.run(["git", "-c", "user.email=mas@local", "-c", "user.name=mas", "commit", "-q", "-m", spec.get("commit", "demo: buggy utilkit with failing tests")], cwd=dest, check=True)
    py = python or sys.executable
    (dest / ".mas").mkdir(exist_ok=True)
    conf = spec["config"](py, fleet, **opts) if callable(spec["config"]) else spec["config"]
    cfg = {**(base_config or {}), **conf, "demo": str(demo)}
    (dest / ".mas" / "config.json").write_text(json.dumps(cfg, indent=2))
    board = SQLiteBoard(dest / ".mas" / "board.db")
    if spec.get("build"):
        items = spec["build"](board, cfg, py, fleet, dest=dest, **opts)
        if cfg.get("github"):
            from .github import GitHubMirror
            gh = GitHubMirror(cfg["github"], labels=cfg.get("github_labels") or [])
            gh.ensure_labels()
            for it in items:
                gh.ensure_issue(it, board)
        return dest, items
    items = []
    assign = spec.get("assign")
    for i, (mod, hint) in enumerate(BRIEFS.items(), 1):
        pref = assign[(i - 1) % len(assign)] if assign else None
        it = Item(id=f"fix-{mod}", title=f"Fix failing tests in src/{mod}.py",
                  brief=(f"Module: src/{mod}.py\nTests: tests/test_{mod}.py\n\nSeveral tests in tests/test_{mod}.py fail. "
                         f"Fix the implementation in src/{mod}.py so the whole test file passes. The tests define correct behaviour — never modify them.\n\nHint: {hint}"),
                  check=f"cmd:{py} -m pytest tests/test_{mod}.py -q", merge_paths=[f"src/{mod}.py"], priority=10 - i,
                  worker_pref=pref, max_attempts=int(cfg.get("max_attempts", 3)))
        board.add(it)
        items.append(it)
    return dest, items
