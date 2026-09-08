"""Live terminal views — materialized from the board's event log (tool 9).

Nothing here changes state. The UI tails `events` and re-reads `items`, so the same
view works for `mas run` (in-process) and `mas watch` (another process, another
orchestrator, another machine sharing the board).
"""
from __future__ import annotations

import json
import os
import threading
import time
from collections import deque
from pathlib import Path
from typing import Optional

from rich import box
from rich.console import Console, Group
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.progress_bar import ProgressBar
from rich.rule import Rule
from rich.spinner import Spinner
from rich.table import Table
from rich.text import Text

from .board import SQLiteBoard, OPEN, LEASED, DONE, PARKED, AWAITING_HUMAN

console = Console()

# ------------------------------------------------------------------ styling
ITEM_PALETTE = ["cyan", "magenta", "green", "yellow", "blue", "bright_magenta", "bright_cyan",
                "bright_green", "bright_yellow", "bright_blue", "orange3", "deep_pink3", "spring_green3", "gold3"]


def item_style(item_id: Optional[str]) -> str:
    if not item_id:
        return "bold white"
    return ITEM_PALETTE[sum(ord(c) for c in item_id) % len(ITEM_PALETTE)]


# kind -> (glyph, style, label)
KINDS = {
    "run_started":        ("▶", "bold white", "run"),
    "run_finished":       ("■", "bold white", "run"),
    "planned":            ("🧭", "bold cyan", "plan"),
    "added":              ("＋", "cyan", "board"),
    "claimed":            ("🔒", "blue", "board"),
    "compartment":        ("🧱", "magenta", "bulkhead"),
    "dispatched":         ("🚀", "bright_blue", "worker"),
    "activity":           ("⚙", "grey62", "worker"),
    "worker_finished":    ("🤖", "white", "worker"),
    "worker_interrupted": ("✋", "yellow", "worker"),
    "fault_injected":     ("⚡", "bold red", "chaos"),
    "gate":               ("🛡", "yellow", "gate"),
    "verified":           ("✅", "green", "gate"),
    "rejected":           ("❌", "red", "gate"),
    "merged":             ("📦", "green", "store"),
    "done":               ("🏁", "bold green", "board"),
    "done_without_lease": ("🏁", "yellow", "board"),
    "failed":             ("✕", "red", "board"),
    "requeued":           ("↻", "yellow", "retry"),
    "parked":             ("⛔", "bold red", "breaker"),
    "lease_expired":      ("⏰", "orange3", "lease"),
    "released":           ("↩", "cyan", "lease"),
    "lesson":             ("💡", "yellow", "memory"),
    "orchestrator_error": ("💥", "bold red", "error"),
    "awaiting_human":     ("🙋", "magenta", "human"),
    "approved":           ("👍", "green", "human"),
    "unparked":           ("🔓", "cyan", "breaker"),
    "edited":             ("✎", "cyan", "contract"),
}
STATUS_STYLE = {OPEN: "grey62", LEASED: "bright_blue", DONE: "green", PARKED: "red", AWAITING_HUMAN: "magenta"}


def _short(s, n=60):
    s = str(s or "")
    s = s.replace("\n", " ⏎ ")
    return s if len(s) <= n else s[: n - 1] + "…"


def _money(x):
    try:
        return f"${float(x):.4f}"
    except (TypeError, ValueError):
        return "$?"


def _last_line(detail: str) -> str:
    lines = [l for l in str(detail or "").splitlines() if l.strip()]
    return lines[-1].strip() if lines else ""


def describe(ev: dict) -> Text:
    """One human sentence per event kind."""
    k, d = ev["kind"], ev.get("data") or {}
    t = Text()
    if k == "run_started":
        t.append("orchestrator started · ", "bold")
        t.append(f"workers {','.join(d.get('workers', []))} · concurrency {d.get('concurrency')} · "
                 f"lease {d.get('lease_s')}s · heartbeat {d.get('heartbeat_s')}s · max_turns {d.get('max_turns')} · "
                 f"timeout {d.get('timeout_s')}s · backoff {d.get('backoff_base')}s×2ⁿ · owner {d.get('owner')}", "grey70")
    elif k == "run_finished":
        s = d.get("stats", {})
        t.append("interrupted" if d.get("interrupted") else "run finished", "bold")
        t.append(f" · {s.get('by_status')} · attempts {s.get('attempts')} · cost {_money(s.get('cost_usd'))}", "grey70")
    elif k == "planned":
        t.append("goal decomposed · ", "bold cyan"); t.append(_short(d.get("goal"), 60), "grey70")
        t.append(f" → {len(d.get('items') or [])} items by {d.get('planner')}", "cyan")
    elif k == "added":
        t.append("added to board · check ", "cyan"); t.append(_short(d.get("check"), 70), "grey70")
    elif k == "claimed":
        t.append(f"claimed · attempt {d.get('attempt')} · lease by ", "blue"); t.append(str(d.get("owner", "?")), "grey62")
    elif k == "compartment":
        t.append(f"{d.get('mode', 'worktree')} ready · ", "magenta"); t.append(_short(d.get("path"), 44), "grey70")
        if d.get("branch"):
            t.append(" · branch ", "grey50"); t.append(d["branch"], "magenta")
    elif k == "dispatched":
        t.append("dispatched → ", "bright_blue"); t.append(f"{d.get('worker')}", "bold bright_blue")
        if d.get("model"):
            t.append(f" ({d['model']})", "bright_blue")
        if d.get("escalated_from"):
            t.append(f" ⬆ escalated from {d['escalated_from']}", "yellow")
        t.append(f" · attempt {d.get('attempt')}", "grey62")
    elif k == "activity":
        t.append(f"{d.get('tool')} ", "bold grey70"); t.append(_short(d.get("arg"), 80), "grey62")
    elif k == "worker_finished":
        t.append("worker finished · ", "white")
        t.append("claims ok" if d.get("ok") else "claims failure", "green" if d.get("ok") else "red")
        bits = []
        if d.get("turns") is not None: bits.append(f"{d['turns']} turns")
        if d.get("cost_usd") is not None: bits.append(_money(d["cost_usd"]))
        elif d.get("tokens"): bits.append(f"{d['tokens'] / 1000:.0f}k tokens")
        if d.get("seconds") is not None: bits.append(f"{d['seconds']}s")
        if bits: t.append(" · " + " · ".join(bits), "grey62")
        if d.get("error"): t.append(" · " + _short(d["error"], 60), "red")
    elif k == "worker_interrupted":
        t.append("worker stopped (graceful shutdown) · attempt refunded", "yellow")
    elif k == "fault_injected":
        t.append("intentional fault · ", "bold red"); t.append(_short(d.get("fault"), 60), "red")
    elif k == "gate":
        t.append("gate running ", "yellow"); t.append(_short(d.get("check"), 80), "grey70")
    elif k == "verified":
        t.append("VERIFIED", "bold green")
        if d.get("worker_claimed_ok") is False: t.append(" (worker had claimed failure!)", "yellow")
        if d.get("detail"): t.append(" · " + _short(_last_line(d["detail"]), 60), "grey62")
    elif k == "rejected":
        t.append("REJECTED by the gate", "bold red")
        if d.get("worker_claimed_ok"): t.append(" — worker claimed success", "yellow")
        if d.get("detail"): t.append(" · " + _short(_last_line(d["detail"]), 60), "grey62")
    elif k == "merged":
        landed = d.get("landed") or []
        t.append(f"landed {len(landed)} file(s) on main", "green")
        if landed: t.append(" · " + _short(", ".join(landed), 50), "grey70")
        if d.get("commit"): t.append(f" · commit {d['commit']}", "bold green")
        if not landed: t.append(" (idempotent: already there)", "grey50")
    elif k == "done":
        t.append("DONE", "bold green"); t.append(f" · {d.get('worker')}", "grey62")
        if d.get("model"): t.append(f" ({d['model']})", "grey62")
        t.append(f" · attempt {d.get('attempt')}", "grey62")
    elif k == "done_without_lease":
        t.append("verified after losing the lease · work landed, board left to the newer attempt", "yellow")
    elif k == "failed":
        t.append("attempt failed", "red")
        if d.get("detail"): t.append(" · " + _short(_last_line(d["detail"]), 60), "grey62")
    elif k == "requeued":
        t.append(f"requeued · backoff {d.get('backoff_s')}s", "yellow")
        if d.get("next_model"): t.append(f" · next: {d.get('next_worker', '')} {d['next_model']}", "yellow")
    elif k == "parked":
        t.append("PARKED — circuit breaker open · ", "bold red"); t.append(str(d.get("reason", "")), "red")
    elif k == "lease_expired":
        t.append("lease expired · owner ", "orange3"); t.append(str(d.get("owner") or "?"), "grey62"); t.append(" stopped renewing → reopened", "orange3")
    elif k == "released":
        t.append("lease handed back · attempt refunded", "cyan")
    elif k == "lesson":
        t.append("lesson: ", "yellow"); t.append(_short(d.get("text"), 90), "grey70")
    elif k == "orchestrator_error":
        t.append("orchestrator error · ", "bold red"); t.append(_short(d.get("error"), 80), "red")
    elif k == "awaiting_human":
        t.append("awaiting human approval · `mas approve`", "magenta")
    elif k == "approved":
        t.append("approved by human", "green")
    elif k == "unparked":
        t.append("unparked · attempts reset", "cyan")
    elif k == "edited":
        t.append("contract edited by a human · ", "cyan"); t.append(", ".join((d.get("changed") or {}).keys()), "grey70")
    else:
        t.append(k, "bold"); t.append(" " + _short(json.dumps(d, default=str), 80), "grey62")
    return t


def format_event(ev: dict, id_width: int = 14) -> Text:
    glyph, style, label = KINDS.get(ev["kind"], ("·", "white", ev["kind"]))
    ts = time.strftime("%H:%M:%S", time.localtime(ev["ts"]))
    line = Text()
    line.append(ts + " ", "grey50")
    line.append(f"{glyph:<2}", style)
    line.append(f"{label:<8} ", style)
    iid = ev.get("item_id") or "—"
    line.append(f"{iid:<{id_width}} ", item_style(ev.get("item_id")))
    line.append_text(describe(ev))
    return line


# ------------------------------------------------------------------ tables
def _fmt_secs(s: float) -> str:
    s = max(0, int(s))
    return f"{s}s" if s < 90 else f"{s // 60}m{s % 60:02d}s"


def board_table(items, now: float, phases: dict, pulses: dict, first_ts: dict) -> Table:
    t = Table(box=box.SIMPLE_HEAD, expand=True, pad_edge=False, show_edge=False, header_style="bold grey70")
    t.add_column("item", no_wrap=True, min_width=12)
    t.add_column("status", no_wrap=True, min_width=14)
    t.add_column("att", justify="center", no_wrap=True, width=5)
    t.add_column("worker", no_wrap=True, min_width=12)
    t.add_column("lease", no_wrap=True, width=8)
    t.add_column("now / last verdict", ratio=1, no_wrap=True)
    settled = {i.id: i.status for i in items if i.status in (DONE, PARKED)}
    for it in items:
        st = it.status
        ok_states = (DONE, PARKED) if (it.meta or {}).get("deps") == "settled" else (DONE,)
        blocked = [d for d in (it.depends_on or []) if settled.get(d) not in ok_states] if st == OPEN else []
        if st == LEASED:
            status = Spinner("dots", text=Text(" working", style="bright_blue"), style="bright_blue")
        elif blocked:
            status = Text(f"⛓ waits for {len(blocked)}", "grey62")
        elif st == DONE:
            status = Text("✓ done", "bold green")
        elif st == PARKED:
            status = Text("⛔ parked", "bold red")
        elif st == AWAITING_HUMAN:
            status = Text("🙋 human", "magenta")
        elif it.next_eligible_at > now:
            status = Text(f"⏳ backoff {_fmt_secs(it.next_eligible_at - now)}", "yellow")
        else:
            status = Text("· open", "grey62")
        att = Text(f"{it.attempts}/{it.max_attempts}", "yellow" if it.attempts > 1 else "grey70")
        v = it.verdict or {}
        ph = phases.get(it.id) or {}
        worker = ""
        if st == LEASED:
            worker = f"{ph.get('worker', '')} {ph.get('model') or ''}".strip()
        elif st == DONE:
            worker = f"{v.get('worker', '')} {v.get('model') or ''}".strip()
        elif v.get("worker"):
            worker = f"{v.get('worker')} {v.get('model') or ''}".strip()
        elif ph.get("worker"):
            worker = f"{ph.get('worker', '')} {ph.get('model') or ''}".strip()
        lease = Text("")
        if st == LEASED:
            left = it.lease_until - now
            heart = "♥" if pulses.get(it.id, 0) > now else "♡"
            lease = Text(f"{heart} {_fmt_secs(left)}", "bold red" if pulses.get(it.id, 0) > now else ("red" if left < 5 else "grey62"))
        if st == LEASED:
            last = Text(ph.get("phase", "…"), "bright_blue")
            if ph.get("since"):
                last.append(f"  ·  {_fmt_secs(now - ph['since'])} in attempt", "grey50")
        elif v.get("detail") or v.get("kind"):
            style = "green" if st == DONE else ("red" if st == PARKED else "grey62")
            last = Text(_short(_last_line(v.get("detail")) or v.get("kind", ""), 60), style)
        elif ph.get("last"):
            last = Text(_short(ph["last"], 60), "grey62")
        else:
            last = Text("—", "grey50")
        t.add_row(Text(it.id, item_style(it.id)), status, att, Text(worker, "grey70"), lease, last)
    return t


def workers_panel(items, now, phases: dict) -> Table:
    t = Table(box=None, expand=True, show_header=False, pad_edge=False)
    t.add_column("w", ratio=1, no_wrap=True)
    live = [it for it in items if it.status == LEASED]
    if not live:
        t.add_row(Text("no workers running", "grey50"))
        return t
    for it in live:
        ph = phases.get(it.id) or {}
        head = Text()
        head.append(f"{ph.get('worker', '?')}", "bold bright_blue")
        if ph.get("model"):
            head.append(f" · {ph['model']}", "bright_blue")
        head.append("  →  ", "grey50"); head.append(it.id, item_style(it.id))
        t.add_row(Group(Spinner("line", text=head, style="bright_blue"),
                        Text("   " + _short(ph.get("phase", "…"), 60), "grey70"),
                        Text(f"   attempt {it.attempts}/{it.max_attempts} · {_fmt_secs(now - ph.get('since', now))} elapsed · "
                             f"{ph.get('activity_n', 0)} tool calls", "grey50")))
    return t


def progress_row(items, stats: dict, t0: float, now: float) -> Table:
    total = len(items) or 1
    done = sum(1 for i in items if i.status == DONE)
    parked = sum(1 for i in items if i.status == PARKED)
    live = sum(1 for i in items if i.status == LEASED)
    bar = ProgressBar(total=total, completed=done, complete_style="green", finished_style="bold green", style="grey35")
    g = Table.grid(expand=True, padding=(0, 1))
    g.add_column(ratio=1); g.add_column(justify="right", no_wrap=True)
    txt = Text()
    txt.append(f"{done}/{len(items)} verified", "bold green")
    txt.append(f" · {live} running", "bright_blue")
    if parked: txt.append(f" · {parked} parked", "red")
    txt.append(f" · attempts {stats.get('attempts', 0)} · turns {stats.get('turns', 0)} · cost {_money(stats.get('cost_usd', 0))}", "grey70")
    if stats.get("tokens"):
        txt.append(f" · {stats['tokens'] / 1000:.0f}k tokens", "grey70")
    txt.append(f" · ⏱ {_fmt_secs(now - t0)}", "grey70")
    g.add_row(bar, txt)
    return g


def header_panel(cfg: dict, title: str) -> Panel:
    chips = Text()
    def chip(k, v, style="cyan"):
        chips.append(f" {k} ", "grey50"); chips.append(f"{v}", style); chips.append("  ")
    chip("workers", ",".join(cfg.get("workers", [])) or "?", "bold cyan")
    chip("concurrency", cfg.get("concurrency", "?"))
    chip("lease", f"{cfg.get('lease_s', '?')}s")
    chip("heartbeat", f"{cfg.get('heartbeat_s', '?'):g}s" if isinstance(cfg.get('heartbeat_s'), (int, float)) else "?")
    chip("max_turns", cfg.get("max_turns", "?"))
    chip("timeout", f"{cfg.get('timeout_s', '?')}s")
    chip("backoff", f"{cfg.get('backoff_base', '?'):g}s×2ⁿ" if isinstance(cfg.get('backoff_base'), (int, float)) else "?")
    chip("breaker", f"{cfg.get('max_attempts', '?')} attempts")
    models = cfg.get("models") or {}
    tiers = " · ".join(f"{k}: {' → '.join(str(m) if m else 'default' for m in (v or [None]))}" for k, v in models.items() if k in (cfg.get("workers") or models.keys()))
    line2 = Text()
    line2.append(" escalation ", "grey50"); line2.append(tiers or "—", "yellow")
    line2.append("   board ", "grey50"); line2.append(_short(cfg.get("board", ""), 60), "grey70")
    return Panel(Group(chips, line2), title=f"[bold]mas[/bold] · {title}", title_align="left", border_style="grey50", box=box.ROUNDED, padding=(0, 1))


# ------------------------------------------------------------------ the live view
class LiveUI:
    """Tails the board and redraws ~8×/s. Use as a context manager."""

    def __init__(self, board: SQLiteBoard, cfg: Optional[dict] = None, title: str = "run", console_: Optional[Console] = None,
                 log_lines: int = 200):
        self.board = board
        self.cfg = dict(cfg or {})
        self.title = title
        self.console = console_ or console
        self.t0 = time.time()
        self.events: deque = deque(maxlen=log_lines)
        self.phases: dict = {}          # item_id -> {worker, model, phase, since, activity_n}
        self.pulses: dict = {}          # item_id -> time until which the heart is lit
        self.lease_seen: dict = {}
        self.first_ts: dict = {}
        self.status_msg = Text("Ctrl-C stops gracefully: workers are killed, leases handed back, attempts refunded", "grey50")
        self.last_seq = 0
        self._stop = threading.Event()
        self._live: Optional[Live] = None
        self._thread: Optional[threading.Thread] = None
        self.cfg.setdefault("board", str(board.path))

    # -- feed
    def status(self, msg: str):
        self.status_msg = Text(msg, "bold white")

    def _ingest(self, ev: dict):
        self.last_seq = max(self.last_seq, ev["seq"])
        k, iid, d = ev["kind"], ev.get("item_id"), ev.get("data") or {}
        if k == "run_started":
            self.cfg.update({kk: vv for kk, vv in d.items() if kk != "root"})
        if k not in ("activity",) or True:
            self.events.append(ev)
        if not iid:
            return
        ph = self.phases.setdefault(iid, {})
        if k == "claimed":
            self.phases[iid] = {"phase": "claimed — preparing compartment", "since": ev["ts"], "activity_n": 0}
        elif k == "compartment":
            ph["phase"] = f"compartment ready · {d.get('mode', 'worktree')}"
        elif k == "dispatched":
            ph.update(worker=d.get("worker"), model=d.get("model"), phase="worker starting…")
        elif k == "activity":
            ph["activity_n"] = ph.get("activity_n", 0) + 1
            ph["phase"] = f"⚙ {d.get('tool')} {_short(d.get('arg'), 40)}"
        elif k == "worker_finished":
            ph["phase"] = "worker finished · " + ("claims ok" if d.get("ok") else "claims failure")
        elif k == "gate":
            ph["phase"] = "🛡 gate: running the check…"
        elif k == "verified":
            ph["phase"] = "✅ verified · landing files"
        elif k == "rejected":
            ph["phase"] = "❌ rejected by the gate"
            ph["last"] = "rejected: " + (_last_line(d.get("detail")) or "check failed")
        elif k == "lease_expired":
            ph["last"] = "lease expired (worker died?)"
        elif k == "merged":
            ph["phase"] = f"📦 landed {len(d.get('landed') or [])} file(s)"

    def _poll(self):
        for ev in self.board.events_since(self.last_seq, 500):
            self._ingest(ev)
        items = self.board.list()
        now = time.time()
        for it in items:
            if it.status == LEASED:
                prev = self.lease_seen.get(it.id)
                if prev is not None and it.lease_until != prev:
                    self.pulses[it.id] = now + 1.2
                self.lease_seen[it.id] = it.lease_until
            else:
                self.lease_seen.pop(it.id, None)
        return items, now

    # -- render
    def _render(self):
        items, now = self._poll()
        stats = self.board.stats()
        height = self.console.size.height
        mid = min(len(items) + 5, max(8, height // 2))     # borders + header + rule, so every item row is visible
        layout = Layout()
        layout.split_column(Layout(name="header", size=4), Layout(name="progress", size=1),
                            Layout(name="mid", size=mid), Layout(name="log", ratio=1), Layout(name="status", size=1))
        layout["mid"].split_row(Layout(name="board", ratio=3), Layout(name="workers", ratio=2))
        layout["header"].update(header_panel(self.cfg, self.title))
        layout["progress"].update(progress_row(items, stats, self.t0, now))
        layout["board"].update(Panel(board_table(items, now, self.phases, self.pulses, self.first_ts), title="[bold]board[/bold] · items", title_align="left", border_style="grey35", box=box.ROUNDED, padding=0))
        layout["workers"].update(Panel(workers_panel(items, now, self.phases), title="[bold]workers[/bold] · in flight", title_align="left", border_style="grey35", box=box.ROUNDED, padding=(0, 1)))
        log_rows = max(3, height - 4 - 1 - mid - 1 - 2)
        lines = [format_event(e) for e in list(self.events)[-log_rows:]]
        layout["log"].update(Panel(Group(*lines) if lines else Text("waiting for events…", "grey50"),
                                   title=f"[bold]event log[/bold] · append-only · seq {self.last_seq}", title_align="left",
                                   border_style="grey35", box=box.ROUNDED, padding=(0, 1)))
        layout["status"].update(self.status_msg)
        return layout

    def _loop(self):
        while not self._stop.wait(0.125):
            try:
                self._live.update(self._render())
            except Exception as e:      # never let the view kill the run
                self.status_msg = Text(f"view error: {e!r}", "red")

    def __enter__(self):
        self._live = Live(self._render(), console=self.console, refresh_per_second=8, screen=False, transient=False)
        self._live.__enter__()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, *exc):
        self._stop.set()
        if self._thread:
            self._thread.join(2)
        try:
            self._live.update(self._render())
        finally:
            self._live.__exit__(*exc)
        return False


# ------------------------------------------------------------------ one-shot views (rich)
def print_events(board: SQLiteBoard, n: int = 40, item_id: Optional[str] = None):
    for ev in board.events(item_id=item_id, limit=n):
        console.print(format_event(ev))


def print_status(board: SQLiteBoard):
    items = board.list()
    now = time.time()
    phases = {}
    for ev in board.events(limit=400):
        if ev.get("item_id") and ev["kind"] == "dispatched":
            phases[ev["item_id"]] = {"worker": ev["data"].get("worker"), "model": ev["data"].get("model"), "phase": "running", "since": ev["ts"]}
    console.print(board_table(items, now, phases, {}, {}))
    s = board.stats()
    console.print(Text(f"{s['total']} items · " + " · ".join(f"{k} {v}" for k, v in s["by_status"].items()) +
                       f" · attempts {s['attempts']} · cost {_money(s['cost_usd'])}", "grey70"))


def print_summary(board: SQLiteBoard, t0: float, interrupted: bool = False):
    items = board.list()
    s = board.stats()
    done = [i for i in items if i.status == DONE]
    parked = [i for i in items if i.status == PARKED]
    first = sum(1 for i in done if i.attempts == 1)
    by_worker: dict = {}
    for i in done:
        w = (i.verdict or {}).get("worker", "?")
        by_worker[w] = by_worker.get(w, 0) + 1
    body = Table.grid(padding=(0, 2))
    body.add_column(style="grey62"); body.add_column()
    body.add_row("verified", Text(f"{len(done)}/{len(items)}", "bold green") + Text(f"  ({first} on the first attempt)", "grey62"))
    body.add_row("attempts", Text(f"{s['attempts']}  ·  turns {s['turns']}", "white"))
    body.add_row("cost", Text(_money(s["cost_usd"]) + (f"  ·  {s['tokens'] / 1000:.0f}k tokens" if s.get("tokens") else ""), "yellow"))
    body.add_row("elapsed", Text(_fmt_secs(time.time() - t0), "white"))
    body.add_row("by worker", Text(" · ".join(f"{k} {v}" for k, v in by_worker.items()) or "—", "bright_blue"))
    if parked:
        body.add_row("parked", Text(", ".join(i.id for i in parked), "bold red") + Text("   → mas show <id> · mas unpark <id>", "grey62"))
    title = "[bold yellow]interrupted — leases handed back[/bold yellow]" if interrupted else ("[bold green]all items verified[/bold green]" if len(done) == len(items) else "[bold]run finished[/bold]")
    console.print(Panel(body, title=title, title_align="left", border_style="green" if len(done) == len(items) and not interrupted else "yellow", box=box.ROUNDED))
