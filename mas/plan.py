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
                "title": {"type": "string"},
                "brief": {"type": "string"},
                "check": {"type": "string"},
                "merge_paths": {"type": "array", "items": {"type": "string"}},
                "priority": {"type": "integer"},
            },
            "required": ["title", "brief", "check"],
        }}
    },
    "required": ["items"],
}

PLAN_PROMPT = """You are decomposing work for a multi-agent system. Split the GOAL into independent, window-sized items that separate workers can do in parallel in isolated copies of this repository, with no dependencies between them.

For EACH item give:
- title: short imperative
- brief: everything a worker needs, pullable cold — files involved, what "done" means, constraints. Never assume the worker saw the other items.
- check: how the orchestrator verifies it: "cmd:<shell command that exits 0 on success>" (e.g. a specific test file), or "human" if no automatic check exists.
- merge_paths: the files this item is allowed to change (leave empty to merge whatever changed).

Rules: aim for {n} items or fewer; every item must be verifiable; if two items would touch the same file, merge them into one. Default test runner: {runner}

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


def plan(goal: str, root: Path, kind: str = "claude", n: int = 12, runner: str = "python -m pytest -q", model: str | None = None) -> list[Item]:
    prompt = PLAN_PROMPT.format(goal=goal, n=n, runner=runner, context=_repo_context(root))
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
    else:
        cmd = ["claude", "-p", prompt, "--output-format", "json", "--json-schema", json.dumps(ITEMS_SCHEMA),
               "--permission-mode", "plan", "--allowedTools", "Read,Grep,Glob"]
        if model:
            cmd += ["--model", model]
        r = subprocess.run(cmd, cwd=root, capture_output=True, text=True, timeout=600)
        out = json.loads(r.stdout.strip().splitlines()[-1])
        data = out.get("structured_output") or json.loads(out.get("result", "{}"))
    items = []
    for i, d in enumerate(data.get("items", []), 1):
        if not d.get("title") or not d.get("brief") or not d.get("check"):
            continue
        items.append(Item(id=f"p{i:02d}", title=d["title"][:120], brief=d["brief"], check=d["check"],
                          merge_paths=list(d.get("merge_paths") or []), priority=int(d.get("priority") or 0)))
    return items
