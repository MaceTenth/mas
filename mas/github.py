"""GitHub Issues as the human-facing board layer (via the `gh` CLI).

import: open issues → items (an issue body may declare its check on a line:  check: cmd:pytest tests/test_x.py)
mirror: verified → close with the verdict; parked → comment with evidence.
"""
from __future__ import annotations

import json
import re
import subprocess

from .board import SQLiteBoard, Item


def _gh(*args) -> str:
    r = subprocess.run(["gh", *args], capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        raise RuntimeError(f"gh {' '.join(args[:3])} failed: {r.stderr.strip()[:200]}")
    return r.stdout


def import_issues(board: SQLiteBoard, repo: str, label: str | None = None, default_check: str = "human", max_attempts: int = 3) -> list[Item]:
    args = ["issue", "list", "-R", repo, "--state", "open", "--json", "number,title,body,labels", "--limit", "200"]
    if label:
        args += ["--label", label]
    issues = json.loads(_gh(*args))
    items = []
    for iss in sorted(issues, key=lambda i: i["number"]):
        iid = f"gh-{iss['number']}"
        if board.get(iid):
            continue
        body = iss.get("body") or ""
        m = re.search(r"^\s*check:\s*(.+)$", body, re.M | re.I)
        check = m.group(1).strip() if m else default_check
        mp = re.search(r"^\s*merge_paths:\s*(.+)$", body, re.M | re.I)
        merge_paths = [p.strip() for p in mp.group(1).split(",")] if mp else []
        wp = re.search(r"^\s*worker:\s*(claude|codex|api)\s*$", body, re.M | re.I)
        item = Item(id=iid, title=iss["title"], brief=body or iss["title"], check=check, merge_paths=merge_paths,
                    max_attempts=max_attempts, worker_pref=wp.group(1).lower() if wp else None,
                    meta={"gh_repo": repo, "gh_number": iss["number"]})
        board.add(item)
        items.append(item)
    return items


class GitHubMirror:
    """Issues as the human-facing trace: one issue per item, one comment per step, close on done.
    Never a scheduler — the board owns claims and leases (Issues have no atomic claim)."""

    def __init__(self, repo: str, labels: list[str] | None = None):
        self.repo = repo
        self.labels = labels or []

    def _num(self, item: Item):
        return item.meta.get("gh_number") if item.meta.get("gh_repo") == self.repo else None

    def _comment(self, item: Item, body: str):
        n = self._num(item)
        if not n:
            return
        try:
            _gh("issue", "comment", str(n), "-R", self.repo, "-b", body)
        except RuntimeError as e:
            print(f"[github] {e}")

    def ensure_issue(self, item: Item, board: SQLiteBoard):
        """Create the issue for an item that was born on the board (not imported)."""
        if self._num(item):
            return self._num(item)
        body = (f"{item.brief}\n\n---\n**mas contract**\n- id: `{item.id}`\n- check: `{item.check}`\n"
                f"- merge_paths: {', '.join(f'`{p}`' for p in item.merge_paths) or '(all changed files)'}\n"
                f"- worker: `{item.worker_pref or 'any'}`" + (f" · model: `{item.meta['model']}`" if item.meta.get("model") else "") +
                (f"\n- depends_on: {', '.join(f'`{d}`' for d in item.depends_on)}" if item.depends_on else "") +
                f"\n- max_attempts: {item.max_attempts}")
        args = ["issue", "create", "-R", self.repo, "-t", item.title[:200], "-b", body]
        for l in self.labels:
            args += ["-l", l]
        try:
            url = _gh(*args).strip()
            n = int(url.rstrip("/").rsplit("/", 1)[-1])
        except (RuntimeError, ValueError) as e:
            print(f"[github] could not create issue for {item.id}: {e}")
            return None
        item.meta.update(gh_repo=self.repo, gh_number=n)
        if board.get(item.id):                              # already on the board → persist; otherwise board.add() will
            board.set_meta(item.id, gh_repo=self.repo, gh_number=n)
        return n

    def ensure_labels(self):
        for l in self.labels:
            try:
                _gh("label", "create", l, "-R", self.repo, "--force", "-c", "5319e7", "-d", "created by mas")
            except RuntimeError:
                pass

    def on_dispatched(self, item: Item, kind: str, model):
        self._comment(item, f"🚀 attempt {item.attempts}/{item.max_attempts} → `{kind}`" + (f" (`{model}`)" if model else "") + " · working in an isolated worktree")

    def on_verdict(self, item: Item, vd: dict, summary: str = ""):
        tail = str(vd.get("detail", "")).strip().splitlines()[-1][:200] if vd.get("detail") else ""
        if vd.get("passed"):
            self._comment(item, f"✅ gate passed · `{item.check}`" + (f" · {tail}" if tail else "") +
                          (f"\n\n<details><summary>worker summary</summary>\n\n{summary[:1500]}\n</details>" if summary else ""))
        else:
            self._comment(item, f"❌ gate rejected attempt {vd.get('attempt')} · `{item.check}`" + (f" · {tail}" if tail else "") +
                          (" — the worker had claimed success" if vd.get("worker_claimed_ok") else ""))

    def on_spawned(self, item: Item, batch: list):
        refs = ", ".join(f"#{b.meta['gh_number']}" if b.meta.get("gh_number") else f"`{b.id}`" for b in batch)
        self._comment(item, f"🧩 planned {len(batch)} item(s): {refs}")

    def on_done(self, item: Item, verdict: dict, landed: list[str]):
        n = self._num(item)
        if not n:
            return
        body = (f"🏁 Verified and landed by mas · worker `{verdict.get('worker')}`" + (f" (`{verdict.get('model')}`)" if verdict.get("model") else "") +
                f" · attempt {verdict.get('attempt')}" + (f" · commit `{verdict.get('commit')}`" if verdict.get("commit") else "") +
                f"\n\nLanded: {', '.join(f'`{p}`' for p in landed) or '(no file changes)'}")
        try:
            _gh("issue", "close", str(n), "-R", self.repo, "-c", body)
        except RuntimeError as e:
            print(f"[github] {e}")

    def on_parked(self, item: Item, verdict: dict):
        self._comment(item, f"⛔ parked after {item.attempts} failed attempts (circuit breaker open).\n\n"
                            f"Last verdict: `{verdict.get('kind')}` — {str(verdict.get('detail', ''))[-600:]}\n\n"
                            f"Reopen for the swarm with `mas unpark {item.id}` after fixing the cause.")
