"""Views: rebuilt from the board's tables for a specific reader. The log is the
truth; these are for reading."""
from __future__ import annotations

import time
from .board import SQLiteBoard

C = {"open": "·", "leased": "⟳", "done": "✓", "parked": "✕", "awaiting_human": "?"}


def fmt_age(ts: float) -> str:
    d = max(0, time.time() - ts)
    return f"{int(d)}s" if d < 90 else f"{int(d / 60)}m" if d < 5400 else f"{d / 3600:.1f}h"


def status_table(board: SQLiteBoard, status: str | None = None) -> str:
    items = board.list(status)
    if not items:
        return "(no items)"
    rows = [f"{'ID':<16} {'ST':<3} {'ATT':<5} {'WORKER':<7} {'TITLE':<44} {'AGE':>5}"]
    for it in items:
        w = (it.verdict or {}).get("worker") or it.worker_pref or "-"
        rows.append(f"{it.id[:16]:<16} {C.get(it.status, '?'):<3} {it.attempts}/{it.max_attempts:<3} {w:<7} {it.title[:44]:<44} {fmt_age(it.updated_at):>5}")
    s = board.stats()
    rows.append(f"\n{s['total']} items · " + " · ".join(f"{k} {v}" for k, v in sorted(s["by_status"].items())) +
                f" · attempts {s['attempts']} · cost≈${s['cost_usd']}")
    return "\n".join(rows)


def show_item(board: SQLiteBoard, item_id: str) -> str:
    it = board.get(item_id)
    if not it:
        return f"no item {item_id}"
    out = [f"{it.id} · {it.title}", f"status {it.status} · attempts {it.attempts}/{it.max_attempts} · check {it.check}",
           f"merge_paths {it.merge_paths or '(all changed files)'}", "", it.brief.strip(), ""]
    if it.verdict:
        out.append("VERDICT: " + " · ".join(f"{k}={v}" for k, v in it.verdict.items() if k != "detail"))
        if it.verdict.get("detail"):
            out.append(it.verdict["detail"][-900:])
        out.append("")
    if it.meta.get("parked_workdir"):
        out.append(f"compartment kept for inspection: {it.meta['parked_workdir']}\n")
    out.append("EVENTS")
    for e in board.events(item_id=item_id, limit=40):
        d = e["data"]
        brief = {k: d[k] for k in ("worker", "model", "attempt", "passed", "turns", "cost_usd", "backoff_s", "reason", "landed", "commit") if k in d and d[k] is not None}
        out.append(f"  {time.strftime('%H:%M:%S', time.localtime(e['ts']))}  {e['kind']:<16} {brief}")
    return "\n".join(out)


def dashboard(board: SQLiteBoard) -> str:
    s = board.stats()
    items = board.list()
    done = [i for i in items if i.status == "done"]
    parked = [i for i in items if i.status == "parked"]
    first_try = sum(1 for i in done if i.attempts == 1)
    by_worker: dict[str, int] = {}
    for i in done:
        w = (i.verdict or {}).get("worker", "?")
        by_worker[w] = by_worker.get(w, 0) + 1
    lines = [
        "DASHBOARD",
        f"  items          {s['total']}  ·  " + "  ".join(f"{k} {v}" for k, v in sorted(s["by_status"].items())),
        f"  success rate   {len(done)}/{s['total']}  ({first_try} on first attempt)",
        f"  attempts       {s['attempts']}  ·  turns {s['turns']}  ·  cost ≈ ${s['cost_usd']}",
        f"  done by worker {by_worker or '-'}",
    ]
    if parked:
        lines.append("  PARKED (breaker open — needs a human):")
        for i in parked:
            lines.append(f"    {i.id}  {i.title[:50]}  →  mas show {i.id}")
    ls = board.lessons(5)
    if ls:
        lines.append("  recent lessons:")
        for l in ls:
            lines.append(f"    - {l['text'][:110]}")
    return "\n".join(lines)


def events_tail(board: SQLiteBoard, limit: int = 30) -> str:
    out = []
    for e in board.events(limit=limit):
        d = e["data"]
        brief = {k: d[k] for k in ("worker", "attempt", "passed", "cost_usd", "backoff_s", "reason", "landed") if k in d}
        out.append(f"{time.strftime('%H:%M:%S', time.localtime(e['ts']))}  {str(e['item_id'] or '-'):<10} {e['kind']:<16} {brief}")
    return "\n".join(out) or "(no events)"
