"""The decomposer: turn a goal into board items — the cut, the contract, the check.

Uses `claude -p --json-schema` (structured output, no API key needed) or `codex exec`.
Items are validated before they touch the board. This is the ONLY place a model
participates in control flow, and its output is checked like any worker's.
"""
from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

from .board import Item

ITEMS_SCHEMA = {
    "type": "object",
    "properties": {
        "items": {"type": "array", "items": {
            "type": "object",
            "properties": {
                "id": {"type": "string", "description": "short slug, unique in this plan"},
                "title": {"type": "string"},
                "brief": {"type": "string"},
                "check": {"type": "string"},
                "merge_paths": {"type": "array", "items": {"type": "string"}},
                "depends_on": {"type": "array", "items": {"type": "string"}, "description": "ids of items whose output this one needs"},
                "priority": {"type": "integer"},
            },
            "required": ["id", "title", "brief", "check"],
        }}
    },
    "required": ["items"],
}

PLAN_PROMPT = """You are decomposing work for a multi-agent system. Split the GOAL into window-sized items that separate workers can do in parallel in isolated copies of this repository. Prefer items with no dependencies; when an item genuinely needs another item's output (a file it lands), say so in depends_on — it will start only after those items are done.

For EACH item give:
- id: a short slug, unique in this plan (e.g. "flights")
- title: short imperative
- brief: everything a worker needs, pullable cold — files involved, what "done" means, constraints. Never assume the worker saw the other items.
- check: how the orchestrator verifies it: "cmd:<shell command that exits 0 on success>" (e.g. a specific test file), or "human" if no automatic check exists.
- merge_paths: the files this item is allowed to change (leave empty to merge whatever changed).
- depends_on: ids of items whose landed files this item reads (usually empty).

Rules: aim for {n} items or fewer; every item must be verifiable; if two items would touch the same file, merge them into one; a check of "human" parks the item for a person to approve. In checks, run Python exactly as: {runner} (never a bare `python`).

GOAL: {goal}

REPOSITORY CONTEXT:
{context}
"""


def _repo_context(root: Path, max_files: int = 120) -> str:
    lines = []
    for p in sorted(root.rglob("*")):
        if p.is_dir() or any(part in {".git", ".mas", "node_modules", ".venv", "__pycache__", ".pytest_cache"} for part in p.parts):
            continue
        rel = str(p.relative_to(root))
        lines.append(rel)
        if len(lines) >= max_files:
            lines.append("…")
            break
    return "\n".join(lines)


def plan(goal: str, root: Path, kind: str = "claude", n: int = 12, runner: str | None = None, model: str | None = None) -> list[Item]:
    import sys
    runner = runner or f"{sys.executable} -m pytest -q"     # a concrete interpreter: a bare `python` may not exist on the machine
    prompt = PLAN_PROMPT.format(goal=goal, n=n, runner=runner, context=_repo_context(root))
    items = _plan(goal, prompt, root, kind, model)
    try:                                              # keep the evidence: what was asked, what came back, what was accepted
        (root / ".mas").mkdir(exist_ok=True)
        (root / ".mas" / "last_plan.json").write_text(json.dumps({"goal": goal, "kind": kind, "model": model, "prompt": prompt,
            "raw": _LAST_RAW.get("data"), "items": [{"id": i.id, "title": i.title, "check": i.check, "merge_paths": i.merge_paths, "depends_on": i.depends_on} for i in items]}, indent=1))
    except OSError:
        pass
    return items


_LAST_RAW: dict = {}


def _plan(goal: str, prompt: str, root: Path, kind: str, model: str | None) -> list[Item]:
    if kind == "codex":
        prompt += "\nRespond with ONLY a JSON object of the form {\"items\": [...]} and nothing else."
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
            last = f.name
        cmd = ["codex", "exec", "-s", "read-only", "-C", str(root), "--skip-git-repo-check", "--output-last-message", last, "--color", "never",
               "-c", "model_reasoning_effort=\"high\""]
        if model:
            cmd += ["-m", model]
        subprocess.run(cmd + [prompt], capture_output=True, text=True, timeout=600)
        text = Path(last).read_text()
        data = json.loads(text[text.index("{"): text.rindex("}") + 1])
        _LAST_RAW["data"] = data
    else:
        cmd = ["claude", "-p", prompt, "--output-format", "json", "--json-schema", json.dumps(ITEMS_SCHEMA),
               "--permission-mode", "plan", "--allowedTools", "Read,Grep,Glob"]
        if model:
            cmd += ["--model", model]
        r = subprocess.run(cmd, cwd=root, capture_output=True, text=True, timeout=600)
        out = json.loads(r.stdout.strip().splitlines()[-1])
        data = out.get("structured_output") or json.loads(out.get("result", "{}"))
        _LAST_RAW["data"] = data
    return parse_plan(data)


def _slug(text: str) -> str:
    import re
    return re.sub(r"[^a-z0-9]+", "-", str(text).lower()).strip("-")[:32] or "item"


def parse_plan(data: dict) -> list[Item]:
    """Validate a planner's JSON into items. Entries without title/brief/check are dropped; ids are
    slugged and made unique; depends_on may name an id or a title and unknown names are dropped."""
    raw = [d for d in (data or {}).get("items", []) if isinstance(d, dict) and d.get("title") and d.get("brief") and d.get("check")]
    ids, seen = [], set()
    for i, d in enumerate(raw, 1):
        iid = _slug(d.get("id") or d["title"])
        while iid in seen:
            iid = f"{iid}-{i}"
        seen.add(iid); ids.append(iid)
    alias = {}
    for d, iid in zip(raw, ids):                       # first writer wins: a duplicate id never steals an earlier item's name
        for key in (iid, _slug(d["title"]), str(d.get("id") or ""), d["title"]):
            alias.setdefault(key, iid)
    items = []
    for d, iid in zip(raw, ids):
        deps = [alias[x] for x in (d.get("depends_on") or []) if x in alias and alias[x] != iid]
        items.append(Item(id=iid, title=d["title"][:120], brief=d["brief"], check=d["check"],
                          merge_paths=list(d.get("merge_paths") or []), priority=int(d.get("priority") or 0), depends_on=deps))
    return items
