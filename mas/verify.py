"""The gate. The orchestrator runs the check itself; a worker's claim is never
evidence. Check specs are strings on the item:

  cmd:<shell command>      exit code 0 in the compartment = pass (tests, build, lint)
  schema:<path>            a JSON file in the compartment must exist and satisfy a
                           minimal schema (required keys + types) given in item.meta["schema"]
  human                    park for a person: `mas approve <id>`
  none                     accept the worker's claim (discouraged; logged loudly)
"""
from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from .board import Item


@dataclass
class Verdict:
    passed: bool
    kind: str
    detail: str = ""
    data: dict = field(default_factory=dict)

    def as_dict(self):
        return {"passed": self.passed, "kind": self.kind, "detail": self.detail[-1500:], **self.data}


def _tail(s: str, n: int = 1500) -> str:
    return s if len(s) <= n else s[:400] + "\n...\n" + s[-(n - 400):]


def check_command(cmd: str, cwd: Path, timeout: int = 300) -> Verdict:
    try:
        r = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return Verdict(False, "cmd", f"check timed out after {timeout}s", {"cmd": cmd})
    out = (r.stdout + r.stderr).strip()
    return Verdict(r.returncode == 0, "cmd", _tail(out), {"cmd": cmd, "returncode": r.returncode})


def check_schema(rel_path: str, cwd: Path, schema: dict) -> Verdict:
    p = cwd / rel_path
    if not p.exists():
        return Verdict(False, "schema", f"{rel_path} not produced")
    try:
        data = json.loads(p.read_text())
    except Exception as e:
        return Verdict(False, "schema", f"{rel_path} is not valid JSON: {e}")
    types = {"string": str, "number": (int, float), "integer": int, "boolean": bool, "array": list, "object": dict}
    problems = []
    for key in schema.get("required", []):
        if key not in data:
            problems.append(f"missing required key: {key}")
    for key, spec in schema.get("properties", {}).items():
        if key in data and "type" in spec and not isinstance(data[key], types.get(spec["type"], object)):
            problems.append(f"{key}: expected {spec['type']}")
    if problems:
        return Verdict(False, "schema", "; ".join(problems))
    return Verdict(True, "schema", f"{rel_path} satisfies schema", {"keys": list(data)[:20]})


def run_check(item: Item, cwd: Path, timeout: int = 300) -> Verdict:
    spec = (item.check or "none").strip()
    if spec.startswith("cmd:"):
        return check_command(spec[4:].strip(), cwd, timeout)
    if spec.startswith("schema:"):
        return check_schema(spec[7:].strip(), cwd, item.meta.get("schema", {}))
    if spec == "human":
        return Verdict(False, "human", "awaiting human approval")
    if spec == "none":
        return Verdict(True, "none", "no verification configured — worker claim accepted (unverified)")
    # bare string: treat as a shell command
    return check_command(spec, cwd, timeout)
