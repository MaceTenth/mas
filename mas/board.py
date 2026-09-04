"""The board: durable task state with atomic claims, expiring leases, and an
append-only event log. Anything satisfying this interface can be a board.

SQLiteBoard is the reference implementation (transactional claim, WAL mode).
mas.github mirrors items to/from GitHub Issues on top of it.
"""
from __future__ import annotations

import json
import random
import sqlite3
import threading
import time
import uuid
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Iterable, Optional

OPEN, LEASED, DONE, PARKED, AWAITING_HUMAN = "open", "leased", "done", "parked", "awaiting_human"


@dataclass
class Item:
    id: str
    title: str
    brief: str
    check: str = "none"                 # "cmd:<shell>" | "schema:<path>" | "human" | "none"
    merge_paths: list = field(default_factory=list)   # files to land on main when verified ([] = all changed)
    status: str = OPEN
    priority: int = 0
    attempts: int = 0
    max_attempts: int = 3
    worker_pref: Optional[str] = None   # "claude" | "codex" | "api" | None
    lease_owner: Optional[str] = None
    lease_until: float = 0.0
    next_eligible_at: float = 0.0
    verdict: Optional[dict] = None
    meta: dict = field(default_factory=dict)
    depends_on: list = field(default_factory=list)     # item ids that must be done (or, with meta.deps="settled", parked) first
    created_at: float = 0.0
    updated_at: float = 0.0

    def to_row(self):
        d = asdict(self)
        d["merge_paths"] = json.dumps(d["merge_paths"])
        d["verdict"] = json.dumps(d["verdict"]) if d["verdict"] is not None else None
        d["meta"] = json.dumps(d["meta"])
        d["depends_on"] = json.dumps(d["depends_on"])
        return d

    @staticmethod
    def from_row(r: sqlite3.Row) -> "Item":
        d = dict(r)
        d["merge_paths"] = json.loads(d["merge_paths"] or "[]")
        d["verdict"] = json.loads(d["verdict"]) if d["verdict"] else None
        d["meta"] = json.loads(d["meta"] or "{}")
        d["depends_on"] = json.loads(d.get("depends_on") or "[]")
        return Item(**d)


SCHEMA = """
CREATE TABLE IF NOT EXISTS items (
  id TEXT PRIMARY KEY, title TEXT, brief TEXT, "check" TEXT, merge_paths TEXT,
  status TEXT, priority INTEGER, attempts INTEGER, max_attempts INTEGER,
  worker_pref TEXT, lease_owner TEXT, lease_until REAL, next_eligible_at REAL,
  verdict TEXT, meta TEXT, depends_on TEXT, created_at REAL, updated_at REAL
);
CREATE INDEX IF NOT EXISTS idx_items_status ON items(status, priority, created_at);
CREATE TABLE IF NOT EXISTS events (
  seq INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL, item_id TEXT, kind TEXT, data TEXT
);
CREATE INDEX IF NOT EXISTS idx_events_item ON events(item_id, seq);
CREATE TABLE IF NOT EXISTS lessons (
  seq INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL, item_id TEXT, text TEXT
);
"""


class SQLiteBoard:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.path), timeout=30, isolation_level=None, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.RLock()          # one connection, many threads (workers, heartbeats, the live view)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA busy_timeout=30000")
        self._conn.executescript(SCHEMA)
        cols = {r[1] for r in self._conn.execute("PRAGMA table_info(items)")}
        if "depends_on" not in cols:                                   # boards created before dependencies existed
            self._conn.execute("ALTER TABLE items ADD COLUMN depends_on TEXT")

    def _exec(self, sql: str, params=()):
        with self._lock:
            return self._conn.execute(sql, params)

    # ---------------- write path ----------------
    def add(self, item: Item) -> Item:
        now = time.time()
        item.created_at = item.created_at or now
        item.updated_at = now
        item.id = item.id or uuid.uuid4().hex[:8]
        row = item.to_row()
        cols = ", ".join(f'"{k}"' for k in row)
        self._exec(f"INSERT OR REPLACE INTO items ({cols}) VALUES ({', '.join('?' for _ in row)})", list(row.values()))
        self.log(item.id, "added", {"title": item.title, "check": item.check})
        return item

    def claim(self, owner: str, lease_seconds: float, worker_kinds: Iterable[str]) -> Optional[Item]:
        """Atomically lease the next eligible open item. Exactly one caller wins."""
        kinds = list(worker_kinds)
        now = time.time()
        self._lock.acquire()
        self._exec("BEGIN IMMEDIATE")
        try:
            q = ("SELECT * FROM items WHERE status=? AND next_eligible_at<=? AND attempts < max_attempts "
                 "AND (worker_pref IS NULL OR worker_pref IN (%s)) "
                 "AND NOT EXISTS (SELECT 1 FROM json_each(COALESCE(items.depends_on, '[]')) d "
                 "                JOIN items i2 ON i2.id = d.value "
                 "                WHERE i2.status != 'done' "
                 "                  AND NOT (COALESCE(json_extract(items.meta, '$.deps'), 'done') = 'settled' AND i2.status = 'parked')) "
                 "AND (COALESCE(json_extract(items.meta, '$.run_last'), 0) = 0 "
                 "     OR NOT EXISTS (SELECT 1 FROM items i3 WHERE i3.id != items.id AND i3.status IN ('open', 'leased') "
                 "                    AND COALESCE(json_extract(i3.meta, '$.run_last'), 0) = 0)) "
                 "ORDER BY priority DESC, created_at ASC LIMIT 1") % ",".join("?" for _ in kinds)
            row = self._exec(q, [OPEN, now, *kinds]).fetchone()
            if not row:
                self._exec("COMMIT")
                return None
            cur = self._exec(
                "UPDATE items SET status=?, lease_owner=?, lease_until=?, attempts=attempts+1, updated_at=? "
                "WHERE id=? AND status=?",
                [LEASED, owner, now + lease_seconds, now, row["id"], OPEN])
            if cur.rowcount != 1:
                self._exec("ROLLBACK")
                return None
            self._exec("COMMIT")
        except Exception:
            self._exec("ROLLBACK")
            raise
        finally:
            self._lock.release()
        item = self.get(row["id"])
        self.log(item.id, "claimed", {"owner": owner, "attempt": item.attempts, "lease_until": item.lease_until})
        return item

    def heartbeat(self, item_id: str, owner: str, lease_seconds: float) -> bool:
        cur = self._exec(
            "UPDATE items SET lease_until=?, updated_at=? WHERE id=? AND status=? AND lease_owner=?",
            [time.time() + lease_seconds, time.time(), item_id, LEASED, owner])
        return cur.rowcount == 1

    def expire_leases(self) -> list[str]:
        """Reopen items whose owner stopped renewing. An item that has already used its
        last attempt is parked instead (the breaker), never re-queued past max_attempts."""
        now = time.time()
        rows = self._exec("SELECT id, lease_owner, attempts, max_attempts FROM items WHERE status=? AND lease_until<?",
                                  [LEASED, now]).fetchall()
        for r in rows:
            if r["attempts"] >= r["max_attempts"]:
                self._exec("UPDATE items SET status=?, lease_owner=NULL, verdict=?, updated_at=? WHERE id=? AND status=?",
                                   [PARKED, json.dumps({"passed": False, "kind": "lease_expired",
                                                        "detail": f"lease expired on attempt {r['attempts']}/{r['max_attempts']} (worker died?)"}),
                                    now, r["id"], LEASED])
                self.log(r["id"], "lease_expired", {"owner": r["lease_owner"]})
                self.log(r["id"], "parked", {"reason": f"lease expired on final attempt {r['attempts']}/{r['max_attempts']}"})
            else:
                self._exec("UPDATE items SET status=?, lease_owner=NULL, updated_at=? WHERE id=? AND status=?",
                                   [OPEN, now, r["id"], LEASED])
                self.log(r["id"], "lease_expired", {"owner": r["lease_owner"]})
        return [r["id"] for r in rows]

    def release(self, item_id: str, owner: str) -> bool:
        """Graceful hand-back (orchestrator shutting down): reopen now and refund the attempt."""
        cur = self._exec(
            "UPDATE items SET status=?, lease_owner=NULL, attempts=MAX(attempts-1, 0), updated_at=? "
            "WHERE id=? AND lease_owner=? AND status=?", [OPEN, time.time(), item_id, owner, LEASED])
        if cur.rowcount == 1:
            self.log(item_id, "released", {"owner": owner})
        return cur.rowcount == 1

    def complete(self, item_id: str, owner: str, verdict: dict) -> bool:
        cur = self._exec(
            "UPDATE items SET status=?, verdict=?, lease_owner=NULL, updated_at=? WHERE id=? AND lease_owner=? AND status=?",
            [DONE, json.dumps(verdict), time.time(), item_id, owner, LEASED])
        ok = cur.rowcount == 1
        if ok:
            self.log(item_id, "done", verdict)
        return ok

    def fail(self, item_id: str, owner: str, verdict: dict, backoff_base: float = 5.0, extra: dict | None = None) -> str:
        """Record a failed attempt. Returns the new status: open (retry later) or parked (breaker opened)."""
        item = self.get(item_id)
        if item is None or item.lease_owner != owner:
            return "lost"
        self.log(item_id, "failed", verdict)
        if item.attempts >= item.max_attempts:
            evidence = [dict(e) for e in self.events(item_id=item_id, limit=50)]
            self._exec("UPDATE items SET status=?, lease_owner=NULL, verdict=?, updated_at=? WHERE id=?",
                               [PARKED, json.dumps({**verdict, "evidence_events": len(evidence)}), time.time(), item_id])
            self.log(item_id, "parked", {"reason": f"{item.attempts} failed attempts", "last": verdict})
            return PARKED
        delay = backoff_base * (2 ** (item.attempts - 1)) * random.uniform(0.7, 1.3)
        self._exec("UPDATE items SET status=?, lease_owner=NULL, next_eligible_at=?, updated_at=? WHERE id=?",
                           [OPEN, time.time() + delay, time.time(), item_id])
        self.log(item_id, "requeued", {"backoff_s": round(delay, 1), **(extra or {})})
        return OPEN

    def await_human(self, item_id: str, owner: str, verdict: dict):
        self._exec("UPDATE items SET status=?, lease_owner=NULL, verdict=?, updated_at=? WHERE id=? AND lease_owner=?",
                           [AWAITING_HUMAN, json.dumps(verdict), time.time(), item_id, owner])
        self.log(item_id, "awaiting_human", verdict)

    def approve(self, item_id: str, note: str = "") -> bool:
        cur = self._exec("UPDATE items SET status=?, updated_at=? WHERE id=? AND status IN (?, ?)",
                                 [DONE, time.time(), item_id, AWAITING_HUMAN, PARKED])
        if cur.rowcount:
            self.log(item_id, "approved", {"note": note})
        return cur.rowcount == 1

    def unpark(self, item_id: str, note: str = "", reset_attempts: bool = True) -> bool:
        cur = self._exec(
            "UPDATE items SET status=?, attempts=CASE WHEN ? THEN 0 ELSE attempts END, next_eligible_at=0, updated_at=? "
            "WHERE id=? AND status IN (?, ?)", [OPEN, 1 if reset_attempts else 0, time.time(), item_id, PARKED, AWAITING_HUMAN])
        if cur.rowcount:
            self.log(item_id, "unparked", {"note": note})
        return cur.rowcount == 1

    def set_meta(self, item_id: str, **kv):
        item = self.get(item_id)
        if item:
            item.meta.update(kv)
            self._exec("UPDATE items SET meta=?, updated_at=? WHERE id=?", [json.dumps(item.meta), time.time(), item_id])

    # ---------------- read path ----------------
    def get(self, item_id: str) -> Optional[Item]:
        r = self._exec("SELECT * FROM items WHERE id=?", [item_id]).fetchone()
        return Item.from_row(r) if r else None

    def list(self, status: Optional[str] = None) -> list[Item]:
        if status:
            rows = self._exec("SELECT * FROM items WHERE status=? ORDER BY priority DESC, created_at", [status])
        else:
            rows = self._exec("SELECT * FROM items ORDER BY created_at")
        return [Item.from_row(r) for r in rows]

    def pending(self) -> int:
        return self._exec("SELECT COUNT(*) FROM items WHERE status IN (?, ?)", [OPEN, LEASED]).fetchone()[0]

    def stats(self) -> dict:
        by = {r[0]: r[1] for r in self._exec("SELECT status, COUNT(*) FROM items GROUP BY status")}
        cost = self._exec("SELECT COALESCE(SUM(json_extract(data,'$.cost_usd')),0) FROM events WHERE kind='worker_finished'").fetchone()[0]
        turns = self._exec("SELECT COALESCE(SUM(json_extract(data,'$.turns')),0) FROM events WHERE kind='worker_finished'").fetchone()[0]
        attempts = self._exec("SELECT COALESCE(SUM(attempts),0) FROM items").fetchone()[0]
        toks = self._exec("SELECT COALESCE(SUM(json_extract(data,'$.tokens')),0) FROM events WHERE kind='worker_finished'").fetchone()[0]
        return {"by_status": by, "total": sum(by.values()), "cost_usd": round(cost or 0, 4), "turns": int(turns or 0),
                "attempts": int(attempts or 0), "tokens": int(toks or 0)}

    # ---------------- log + lessons (append-only) ----------------
    def log(self, item_id: Optional[str], kind: str, data: dict | None = None):
        self._exec("INSERT INTO events (ts, item_id, kind, data) VALUES (?, ?, ?, ?)",
                           [time.time(), item_id, kind, json.dumps(data or {}, default=str)])

    def events(self, item_id: Optional[str] = None, limit: int = 200) -> list[dict]:
        if item_id:
            rows = self._exec("SELECT * FROM events WHERE item_id=? ORDER BY seq DESC LIMIT ?", [item_id, limit])
        else:
            rows = self._exec("SELECT * FROM events ORDER BY seq DESC LIMIT ?", [limit])
        out = []
        for r in rows:
            d = dict(r)
            d["data"] = json.loads(d["data"] or "{}")
            out.append(d)
        return list(reversed(out))

    def events_since(self, seq: int, limit: int = 500) -> list[dict]:
        rows = self._exec("SELECT * FROM events WHERE seq>? ORDER BY seq ASC LIMIT ?", [seq, limit])
        out = []
        for r in rows:
            d = dict(r)
            d["data"] = json.loads(d["data"] or "{}")
            out.append(d)
        return out

    def add_lesson(self, text: str, item_id: Optional[str] = None):
        self._exec("INSERT INTO lessons (ts, item_id, text) VALUES (?, ?, ?)", [time.time(), item_id, text[:600]])
        self.log(item_id, "lesson", {"text": text[:600]})

    def lessons(self, limit: int = 12) -> list[dict]:
        rows = self._exec("SELECT * FROM lessons ORDER BY seq DESC LIMIT ?", [limit]).fetchall()
        return [dict(r) for r in reversed(rows)]
