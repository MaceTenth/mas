"""The orchestrator: plain code, no LLM in the loop. Restartable — every state
change is a board write, so it can be killed at any moment and resumed.

loop:  expire leases → claim → compartment → worker → GATE → merge (idempotent)
       → done | requeue with backoff + escalation | park (circuit breaker)

Ctrl-C / SIGTERM is a graceful stop: live workers are killed, their leases are
handed back with the attempt refunded, and the next `mas run` continues at once.
SIGKILL (or a power cut) is also fine — leases simply expire.
"""
from __future__ import annotations

import concurrent.futures as cf
import itertools
import json
import os
import re
import signal
import socket
import threading
import time
import uuid
from pathlib import Path
from typing import Optional

from .board import SQLiteBoard, Item, DONE, PARKED, AWAITING_HUMAN
from .verify import run_check
from .workers import make_worker, build_prompt, kill_children, STOP
from .workspace import Workspace


class Orchestrator:
    def __init__(self, board: SQLiteBoard, workspace: Workspace, config: dict, worker_kinds: list[str],
                 concurrency: int = 4, github=None, log=print, activity_log=None):
        self.board, self.ws, self.cfg = board, workspace, config
        self.kinds = worker_kinds or ["claude"]
        self.concurrency = concurrency
        self.github = github
        self.log = log
        self.activity_log = activity_log          # plain mode prints worker tool calls; the live view reads them from the board
        self.max_attempts = int(config.get("max_attempts", 3))
        self.lease_s = float(config.get("lease_seconds", 600))
        # invariant: a live worker must renew well before its lease expires (heartbeat ≤ lease/3),
        # otherwise healthy workers get their items re-claimed and work is duplicated.
        self.heartbeat_s = min(float(config.get("heartbeat_seconds", 30)), max(1.0, self.lease_s / 3))
        self.budget_turns = int(config.get("max_turns", 20))
        self.timeout_s = int(config.get("attempt_timeout_seconds", 900))
        self.check_timeout = int(config.get("check_timeout_seconds", 300))
        self.backoff_base = float(config.get("backoff_base_seconds", 5))
        self.models = config.get("models", {"claude": ["haiku", "sonnet"], "codex": [None], "api": ["claude-haiku-4-5-20251001", "claude-sonnet-5"]})
        self.commit = bool(config.get("commit_on_merge", True))
        self._rr = itertools.cycle(self.kinds)
        self._owner_base = f"{socket.gethostname()}-{uuid.uuid4().hex[:6]}"
        self._inflight: dict[str, str] = {}      # item_id -> owner, for graceful release on stop
        self._released: set = set()
        self._lock = threading.Lock()
        self.stopping = threading.Event()
        self.interrupted = False

    # ---------------- policy ----------------
    def _pick_kind(self, item: Item) -> str:
        if item.worker_pref and item.worker_pref in self.kinds:
            return item.worker_pref
        return next(self._rr)

    def _model_for(self, kind: str, attempt: int) -> Optional[str]:
        tiers = self.models.get(kind) or [None]
        return tiers[min(max(attempt - 1, 0), len(tiers) - 1)]   # escalate on retry

    # ---------------- one item ----------------
    def process(self, item: Item, owner: str):
        kind = self._pick_kind(item)
        # a pinned model applies to the first attempt; retries escalate through the kind's tiers (never below the pin)
        tiers = self.models.get(kind) or [None]
        pinned = item.meta.get("model")
        if pinned and (item.attempts <= 1 or pinned not in tiers):
            model = pinned
        elif pinned:
            model = tiers[min(tiers.index(pinned) + item.attempts - 1, len(tiers) - 1)]
        else:
            model = self._model_for(kind, item.attempts)
        self.log(f"[{item.id}] attempt {item.attempts}/{item.max_attempts} → {kind}" + (f" ({model})" if model else ""))
        key = f"{item.id}-a{item.attempts}"          # one compartment per attempt, never shared
        path = self.ws.prepare(key)
        rel = os.path.relpath(path, self.ws.root)
        mode = "worktree" if self.ws.is_git else "copy"
        self.board.log(item.id, "compartment", {"path": rel, "branch": f"mas/{key}" if self.ws.is_git else None, "mode": mode})
        self.log(f"[{item.id}] compartment {rel} ({mode}{', branch mas/' + key if self.ws.is_git else ''})")
        prev_model = (item.meta.get("model") if item.attempts == 2 and item.meta.get("model") else self._model_for(kind, item.attempts - 1)) if item.attempts > 1 else None
        self.board.log(item.id, "dispatched", {"worker": kind, "model": model, "attempt": item.attempts, "path": str(path),
                                               "escalated_from": prev_model if prev_model and prev_model != model else None})
        if self.github:
            self.github.on_dispatched(item, kind, model)

        stop = threading.Event()
        def beat():
            while not stop.wait(self.heartbeat_s):
                if not self.board.heartbeat(item.id, owner, self.lease_s):
                    self.log(f"[{item.id}] lost lease — another worker owns it now"); stop.set()
        threading.Thread(target=beat, daemon=True).start()

        check_cmd = item.check[4:] if item.check.startswith("cmd:") else None
        worker = make_worker(kind, self.cfg, check_cmd=check_cmd, context={"board": str(self.board.path), "root": str(self.ws.root)})
        lessons = [l["text"] for l in self.board.lessons(6)] if self.cfg.get("share_lessons", True) else []
        prompt = build_prompt(item.title, item.brief, item.check, lessons)

        def on_activity(tool: str, arg: str):
            self.board.log(item.id, "activity", {"tool": tool, "arg": str(arg)[:200], "worker": kind, "model": model})
            if self.activity_log:
                self.activity_log(f"[{item.id}]   ⚙ {tool} {' ⏎ '.join(str(arg).split(chr(10)))[:110]}")

        try:
            result = worker.run(prompt, path, model, self.budget_turns, self.timeout_s, on_activity=on_activity)
        except Exception as e:
            from .workers import WorkerResult
            result = WorkerResult(False, error=f"worker crashed: {e!r}")
        finally:
            stop.set()
        if self.stopping.is_set():
            # graceful stop: hand the lease back (attempt refunded); nothing is gated or merged
            self.board.log(item.id, "worker_interrupted", {"worker": kind, "model": model, "attempt": item.attempts})
            self._release(item.id, owner)
            self.ws.cleanup(key, path)
            return
        self.board.log(item.id, "worker_finished", {**result.as_dict(), "worker": kind, "model": model})

        # ---- the gate: never trust the worker ----
        self.board.log(item.id, "gate", {"check": item.check, "worker_claimed_ok": result.ok})
        self.log(f"[{item.id}] gate: {item.check[:90]}")
        verdict = run_check(item, path, self.check_timeout)
        vd = {**verdict.as_dict(), "worker": kind, "model": model, "worker_claimed_ok": result.ok, "attempt": item.attempts}
        self.board.log(item.id, "verified" if verdict.passed else "rejected", vd)
        if self.github:
            self.github.on_verdict(item, vd, result.summary)

        if verdict.kind == "human":
            landed = self.ws.merge(path, item.merge_paths)      # stage the work; a human decides
            self.board.await_human(item.id, owner, {**vd, "landed": landed})
            self.log(f"[{item.id}] awaiting human approval ({len(landed)} files staged)")
            self.ws.cleanup(key, path)
            return

        if verdict.passed:
            landed = self.ws.merge(path, item.merge_paths)      # idempotent
            sha = self.ws.commit(f"mas: {item.title} [{item.id}]", landed) if self.commit else None
            self.board.log(item.id, "merged", {"landed": landed, "commit": sha})
            spawned = self._spawn(item) if item.meta.get("spawn") else []      # children exist BEFORE the parent is done
            ok = self.board.complete(item.id, owner, {**vd, "landed": landed, "commit": sha, "spawned": spawned})
            if ok and result.summary and self.cfg.get("share_lessons", True):
                first = result.summary.strip().split("\n")[0][:240]
                if first:
                    self.board.add_lesson(f"[{item.title}] {first}", item.id)
            if ok:
                if self.github:
                    self.github.on_done(item, vd, landed)
                self.log(f"[{item.id}] ✓ verified · landed {len(landed)} file(s)" + (f" · {sha}" if sha else ""))
            else:
                # verified work is still landed (idempotent), but this attempt no longer owns the item:
                # its lease expired and another attempt took over. The board is left to the owner.
                self.board.log(item.id, "done_without_lease", {**vd, "landed": landed, "commit": sha})
                self.log(f"[{item.id}] ✓ verified · landed {len(landed)} file(s) · lease was lost, board left to the newer attempt")
            self.ws.cleanup(key, path)
            return

        nxt = self._model_for(kind, item.attempts + 1)
        status = self.board.fail(item.id, owner, {**vd, "worker_summary": result.summary[:400], "worker_error": result.error},
                                 self.backoff_base, extra={"next_model": nxt, "next_worker": kind})
        if status == PARKED:
            self.log(f"[{item.id}] ✕ parked after {item.attempts} attempts — evidence: `mas show {item.id}`")
            if self.github:
                self.github.on_parked(item, vd)
            # keep the compartment for inspection
            self.board.set_meta(item.id, parked_workdir=str(path))
        elif status == "lost":
            self.log(f"[{item.id}] ✕ rejected, and the lease was lost meanwhile — nothing recorded")
            self.ws.cleanup(key, path)
        else:
            self.log(f"[{item.id}] ✕ rejected ({verdict.detail.splitlines()[-1][:80] if verdict.detail else 'no detail'}) — will retry with escalation")
            self.ws.cleanup(key, path)

    # ---------------- the loop ----------------
    def run(self, forever: bool = False, max_items: Optional[int] = None, poll_s: float = 3.0):
        processed = 0
        self.log(f"mas run · workers={','.join(self.kinds)} · concurrency={self.concurrency} · lease={int(self.lease_s)}s · "
                 f"heartbeat={self.heartbeat_s:g}s · max_turns={self.budget_turns} · timeout={self.timeout_s}s · "
                 f"backoff={self.backoff_base:g}s×2ⁿ · breaker={self.max_attempts} attempts · board={self.board.path}")
        self.board.log(None, "run_started", self.describe_config())
        self._install_signal_handlers()
        with cf.ThreadPoolExecutor(max_workers=self.concurrency) as ex:
            futures = set()
            idle_since = None
            while not self.stopping.is_set():
                expired = self.board.expire_leases()
                for e in expired:
                    it = self.board.get(e)
                    self.log(f"[{e}] lease expired → " + ("parked (final attempt)" if it and it.status == PARKED else "reopened"))
                futures = {f for f in futures if not f.done()}
                while len(futures) < self.concurrency and (max_items is None or processed < max_items) and not self.stopping.is_set():
                    owner = f"{self._owner_base}-{uuid.uuid4().hex[:4]}"
                    item = self.board.claim(owner, self.lease_s, self.kinds)
                    if item is None:
                        break
                    processed += 1
                    with self._lock:
                        self._inflight[item.id] = owner
                    futures.add(ex.submit(self._guard, item, owner))
                if not futures:
                    if self.board.pending() == 0 or (max_items is not None and processed >= max_items):
                        if not forever:
                            break
                    # nothing claimable right now (backoff / waiting) — idle
                    idle_since = idle_since or time.time()
                    if not forever and self.board.pending() > 0 and time.time() - idle_since > self.lease_s + 60:
                        self.log("nothing claimable for a full lease period — exiting; items in backoff will be picked up next run")
                        break
                else:
                    idle_since = None
                self.stopping.wait(poll_s)
            if self.stopping.is_set():
                killed = self._release_all()
        if self.stopping.is_set():
            self.log(f"stopped {killed} worker process(es) · released {len(self._released)} lease(s): {', '.join(sorted(self._released)) or '-'}")
        s = self.board.stats()
        self.board.log(None, "run_finished", {"stats": s, "interrupted": self.interrupted, "owner": self._owner_base})
        self.log(("interrupted" if self.interrupted else "done") + f" · {s['by_status']} · attempts={s['attempts']} · cost≈${s['cost_usd']}")
        return s

    # ---------------- spawn: a finished item can put new items on the board ----------------
    def _spawn(self, item: Item) -> list[str]:
        """item.meta["spawn"] = {"file": "PLAN.json", "key": "items", "defaults": {...}, "after": [templates]}
        The file (landed on main by this item) holds a list of item dicts: title, brief, check required;
        id, merge_paths, worker, model, depends_on, priority, max_attempts, meta optional. depends_on may
        name other ids in the same batch. Every template in "after" is added with depends_on = the whole
        batch (plus its own), so a reviewer/scorer can follow a planner. Nothing is trusted: bad entries are
        skipped and logged."""
        spec = item.meta["spawn"] if isinstance(item.meta.get("spawn"), dict) else {"file": item.meta["spawn"]}
        path = self.ws.root / spec.get("file", "PLAN.json")
        try:
            data = json.loads(path.read_text())
        except Exception as e:
            self.board.log(item.id, "spawn_failed", {"file": str(path), "error": repr(e)})
            self.log(f"[{item.id}] spawn: cannot read {path.name}: {e!r}")
            return []
        entries = data.get(spec.get("key", "items"), data) if isinstance(data, dict) else data
        if not isinstance(entries, list):
            entries = []
        defaults = spec.get("defaults") or {}
        prefix = spec.get("prefix", "")
        batch: list[Item] = []
        for i, e in enumerate(entries, 1):
            if not isinstance(e, dict) or not e.get("title") or not e.get("brief") or not e.get("check"):
                self.board.log(item.id, "spawn_skipped", {"index": i, "reason": "needs title, brief, check"})
                continue
            iid = prefix + str(e.get("id") or re.sub(r"[^a-z0-9]+", "-", e["title"].lower()).strip("-")[:32])
            if self.board.get(iid):
                iid = f"{iid}-{uuid.uuid4().hex[:4]}"
            meta = {**(defaults.get("meta") or {}), **(e.get("meta") or {})}
            if e.get("model") or defaults.get("model"):
                meta["model"] = e.get("model") or defaults.get("model")
            batch.append(Item(id=iid, title=str(e["title"])[:120], brief=str(e["brief"]) + str(defaults.get("brief_suffix", "")), check=str(e["check"]),
                              merge_paths=list(e.get("merge_paths") or []), priority=int(e.get("priority", defaults.get("priority", 5))),
                              max_attempts=int(e.get("max_attempts", defaults.get("max_attempts", self.max_attempts))),
                              worker_pref=e.get("worker") or defaults.get("worker"), depends_on=list(e.get("depends_on") or []), meta=meta))
        ids = {b.id for b in batch}
        alias = {b.title: b.id for b in batch}               # depends_on may name a batch entry by raw id, prefixed id, or title
        for e, b in zip([x for x in entries if isinstance(x, dict) and x.get("title") and x.get("brief") and x.get("check")], batch):
            if e.get("id"):
                alias[str(e["id"])] = b.id
        for b in batch:
            resolved = []
            for d in b.depends_on:
                r = alias.get(d, d)
                if r in ids or self.board.get(r):
                    resolved.append(r)
                else:
                    self.board.log(item.id, "spawn_skipped", {"item": b.id, "reason": f"unknown dependency {d!r}"})
            b.depends_on = resolved
        for tpl in (spec.get("after") or []) if batch else []:      # no batch → nothing to review, no `after`
            tid = str(tpl.get("id") or (prefix + "after"))
            if self.board.get(tid):
                tid = f"{tid}-{uuid.uuid4().hex[:4]}"
            meta = dict(tpl.get("meta") or {})
            if tpl.get("model"):
                meta["model"] = tpl["model"]
            batch.append(Item(id=tid, title=tpl["title"], brief=tpl["brief"], check=tpl.get("check", "none"),
                              merge_paths=list(tpl.get("merge_paths") or []), priority=int(tpl.get("priority", 1)),
                              max_attempts=int(tpl.get("max_attempts", self.max_attempts)), worker_pref=tpl.get("worker"),
                              depends_on=sorted(ids) + list(tpl.get("depends_on") or []), meta=meta))
        for b in batch:
            if self.github:
                self.github.ensure_issue(b, self.board)   # issue number goes into b.meta BEFORE the item is claimable
            self.board.add(b)
        self.board.log(item.id, "spawned", {"file": path.name, "items": [b.id for b in batch]})
        if not batch:
            self.log(f"[{item.id}] spawned nothing ({path.name} had no valid entries)")
            if self.github:
                self.github.on_spawned(item, batch)
            return []
        self.log(f"[{item.id}] spawned {len(batch)} item(s): {', '.join(b.id for b in batch)}")
        if self.github:
            self.github.on_spawned(item, batch)
        return [b.id for b in batch]

    def describe_config(self) -> dict:
        return {"workers": self.kinds, "concurrency": self.concurrency, "lease_s": int(self.lease_s), "heartbeat_s": round(self.heartbeat_s, 1),
                "max_turns": self.budget_turns, "timeout_s": self.timeout_s, "backoff_base": self.backoff_base,
                "max_attempts": self.max_attempts, "models": {k: self.models.get(k) for k in self.kinds},
                "owner": self._owner_base, "pid": os.getpid(), "root": str(self.ws.root), "board": str(self.board.path)}

    def stop(self):
        """Graceful stop: kill live workers, hand leases back (attempt refunded), return."""
        self.interrupted = True
        self.stopping.set()

    def _install_signal_handlers(self):
        if threading.current_thread() is not threading.main_thread():
            return
        def handler(signum, frame):
            if not self.stopping.is_set():
                self.log(f"received {signal.Signals(signum).name} — stopping workers and releasing leases (Ctrl-C again to abort)")
                self.stop()
            else:
                raise KeyboardInterrupt
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                signal.signal(sig, handler)
            except (ValueError, OSError):
                pass

    def _release(self, item_id: str, owner: str) -> bool:
        ok = self.board.release(item_id, owner)
        if ok:
            with self._lock:
                self._released.add(item_id)
        return ok

    def _release_all(self) -> int:
        """Snapshot the in-flight set BEFORE killing workers: a killed worker's thread may
        finish and drop out of _inflight while we are still killing the others. Both this
        method and the thread release the lease; ownership makes the second call a no-op."""
        with self._lock:
            inflight = dict(self._inflight)
        killed = kill_children()
        for item_id, owner in inflight.items():
            self._release(item_id, owner)
        return killed

    def _guard(self, item: Item, owner: str):
        try:
            self.process(item, owner)
        except Exception as e:
            self.board.log(item.id, "orchestrator_error", {"error": repr(e)})
            if not self.stopping.is_set():
                self.board.fail(item.id, owner, {"passed": False, "kind": "error", "detail": repr(e)}, self.backoff_base)
                self.log(f"[{item.id}] orchestrator error: {e!r}")
        finally:
            with self._lock:
                self._inflight.pop(item.id, None)
