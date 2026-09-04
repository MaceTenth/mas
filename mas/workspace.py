"""Compartments (bulkheads) and the artifact store.

Each attempt works in its own git worktree (or a plain copy when the project
is not a git repo). Only verified files land on main, idempotently — landing the
same verified result twice changes nothing.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

NOISE = {".git", ".mas", "__pycache__", ".pytest_cache", "node_modules", ".venv", "venv", ".mypy_cache", ".ruff_cache"}
IGNORE = shutil.ignore_patterns(*NOISE)


class Workspace:
    def __init__(self, root: str | Path):
        self.root = Path(root).resolve()
        self.work = self.root / ".mas" / "work"
        self.work.mkdir(parents=True, exist_ok=True)
        self.is_git = (self.root / ".git").exists()
        if self.is_git:
            gi = self.root / ".gitignore"
            text = gi.read_text() if gi.exists() else ""
            if ".mas/" not in text:
                gi.write_text(text.rstrip("\n") + ("\n" if text else "") + ".mas/\n")

    def _git(self, *args, cwd=None, check=True):
        return subprocess.run(["git", *args], cwd=cwd or self.root, capture_output=True, text=True, check=check)

    def prepare(self, key: str) -> Path:
        """Create the compartment for one attempt. `key` is unique per attempt
        (e.g. "fix-lru-a2"), so a stale worker from a lost lease can never share
        a directory or branch with the attempt that replaced it."""
        path = self.work / key
        if path.exists():
            self.cleanup(key, path)
        if self.is_git:
            branch = f"mas/{key}"
            self._git("worktree", "prune", check=False)
            self._git("branch", "-D", branch, check=False)
            self._git("worktree", "add", "-q", "-b", branch, str(path), "HEAD")
        else:
            shutil.copytree(self.root, path, ignore=IGNORE)
        return path

    def changed_files(self, path: Path) -> list[str]:
        if self.is_git:
            out = self._git("status", "--porcelain", cwd=path).stdout
            files = []
            for line in out.splitlines():
                name = line[3:].strip().strip('"')
                if " -> " in name:
                    name = name.split(" -> ", 1)[1]
                if not name or name.endswith("/") or name.startswith(".mas"):
                    continue                      # directories (untracked dirs) and our own state are never merged
                if any(part in NOISE for part in Path(name).parts):
                    continue
                files.append(name)
            return files
        # non-git fallback: compare file hashes against root
        changed = []
        for p in path.rglob("*"):
            if p.is_dir() or any(part in {".mas", ".git", "__pycache__", "node_modules", ".venv"} for part in p.parts):
                continue
            rel = p.relative_to(path)
            q = self.root / rel
            if not q.exists() or q.read_bytes() != p.read_bytes():
                changed.append(str(rel))
        return changed

    def merge(self, path: Path, merge_paths: list[str] | None) -> list[str]:
        """Land verified files on main. Idempotent: identical content is a no-op.
        merge_paths entries are files, or directory prefixes ending in "/" (all changed files under them);
        an empty list means every changed file."""
        changed = self.changed_files(path)
        if merge_paths:
            files = []
            for mp in merge_paths:
                if mp.endswith("/"):                       # a directory prefix: every changed file under it
                    files += [c for c in changed if c.startswith(mp)]
                else:
                    files.append(mp)
        else:
            files = changed
        landed = []
        for rel in files:
            src = path / rel
            dst = self.root / rel
            if not src.exists() or src.is_dir():
                continue
            if dst.exists() and dst.read_bytes() == src.read_bytes():
                continue
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            landed.append(rel)
        return landed

    def commit(self, message: str, files: list[str]) -> str | None:
        if not self.is_git or not files:
            return None
        self._git("add", "--", *files)
        r = self._git("commit", "-q", "-m", message, check=False)
        if r.returncode != 0:
            return None
        return self._git("rev-parse", "--short", "HEAD").stdout.strip()

    def cleanup(self, key: str, path: Path):
        if self.is_git:
            self._git("worktree", "remove", "--force", str(path), check=False)
            self._git("branch", "-D", f"mas/{key}", check=False)
        if path.exists():
            shutil.rmtree(path, ignore_errors=True)
