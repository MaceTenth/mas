#!/usr/bin/env python3
"""Compare Demo 5 variants from their boards and the external quality oracle."""
from __future__ import annotations

import argparse
import json
import sqlite3
import subprocess
import sys
from pathlib import Path


VARIANTS = {
    "small-alone": "GPT-5.4 Mini alone",
    "small-direct-context": "GPT-5.4 Mini + direct private context",
    "advised": "GPT-5.4 Mini + GPT-5.5 adviser",
    "strong-alone": "GPT-5.5 alone",
}


def _json(text: str | None):
    try:
        return json.loads(text or "{}")
    except Exception:
        return {}


def read_variant(root: Path, score_script: Path) -> dict | None:
    db = root / ".mas" / "board.db"
    if not db.exists():
        return None
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    item = con.execute("SELECT * FROM items WHERE id='authorize'").fetchone()
    events = list(con.execute("SELECT ts, kind, data FROM events ORDER BY seq"))
    con.close()
    if item is None:
        return None
    meta = _json(item["meta"])
    candidate = root if item["status"] == "done" else Path(meta.get("parked_workdir") or root)
    scored = subprocess.run([sys.executable, str(score_script), str(candidate), "--json"], capture_output=True, text=True)
    try:
        quality = json.loads(scored.stdout)
    except Exception:
        quality = {"passed": 0, "total": 50, "quality": 0.0, "sections": {},
                   "failures": [{"case": "score", "error": scored.stderr[-200:]}]}
    worker_events = [_json(e["data"]) for e in events if e["kind"] == "worker_finished"]
    starts = [e["ts"] for e in events if e["kind"] == "run_started"]
    finishes = [e["ts"] for e in events if e["kind"] == "run_finished"]
    wall = (max(finishes) - min(starts)) if starts and finishes else sum(float(e.get("seconds") or 0) for e in worker_events)
    breakdown = next((e.get("breakdown") for e in reversed(worker_events) if e.get("breakdown")), {})
    advisor = (breakdown or {}).get("advisor") or {}
    return {
        "status": item["status"], "quality": quality,
        "wall_seconds": round(wall, 1),
        "tokens": sum(int(e.get("tokens") or 0) for e in worker_events),
        "cost_usd": round(sum(float(e.get("cost_usd") or 0) for e in worker_events), 4),
        "turns": sum(int(e.get("turns") or 0) for e in worker_events),
        "advisor_calls": int(advisor.get("calls") or 0),
        "successful_advice": int(advisor.get("successful_calls") or 0),
        "checkpoint_satisfied": bool(advisor.get("checkpoint_satisfied", True)),
        "breakdown": breakdown,
    }


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("base")
    p.add_argument("variants", nargs="*", choices=list(VARIANTS))
    args = p.parse_args(argv)
    base = Path(args.base).resolve()
    score_script = Path(__file__).with_name("score.py")
    selected = set(args.variants or VARIANTS)
    results = {name: read_variant(base / name, score_script) if name in selected else None for name in VARIANTS}
    present = {k: v for k, v in results.items() if v is not None}
    lines = ["# Demo 5 · Advice as private context", "",
             "One authorization-engine task, four independent runs. Public semantics are available to every executor. "
             "The direct-context Mini and the adviser receive the identical private Cerulean-7 packet; in the advised arm, "
             "Mini can access it only through a mandatory read-only consultation.", "",
             "| variant | architecture | total | public | private profile | status | wall | tokens | cost | turns | advice |",
             "|---|---|---:|---:|---:|---|---:|---:|---:|---:|---:|"]
    for name, label in VARIANTS.items():
        result = results[name]
        if result is None:
            lines.append(f"| `{name}` | {label} | not run | — | — | — | — | — | — | — | — |")
            continue
        q = result["quality"]
        public = q.get("sections", {}).get("public_contract", {})
        private = q.get("sections", {}).get("private_profile", {})
        advice = f"{result['successful_advice']}/{result['advisor_calls']}"
        lines.append(f"| `{name}` | {label} | {q['passed']}/{q['total']} ({q['quality']:.0%}) | "
                     f"{public.get('passed', 0)}/{public.get('total', 0)} | {private.get('passed', 0)}/{private.get('total', 0)} | {result['status']} | "
                     f"{result['wall_seconds']:.1f}s | {result['tokens']:,} | ${result['cost_usd']:.4f} | "
                     f"{result['turns']} | {advice} |")
    if "small-alone" in present and "advised" in present:
        small = present["small-alone"]["quality"]["passed"]
        advised = present["advised"]["quality"]["passed"]
        lines += ["", f"Adviser lift over the small model alone: **{advised - small:+d} oracle cases**. "
                  "Advice is shown as successful/attempted calls. This experiment intentionally changes information access, "
                  "so it demonstrates context routing rather than isolating model intelligence. Repeat across seeds/tasks "
                  "before making a general performance claim."]
    if "small-alone" in present and "small-direct-context" in present:
        small = present["small-alone"]["quality"]["passed"]
        direct = present["small-direct-context"]["quality"]["passed"]
        lines += [f"Direct-context lift over the small model alone: **{direct - small:+d} oracle cases**."]
    if "small-direct-context" in present and "advised" in present:
        direct = present["small-direct-context"]["quality"]["passed"]
        advised = present["advised"]["quality"]["passed"]
        lines += [f"Adviser lift over direct context: **{advised - direct:+d} oracle cases**."]
    lines += ["", "## Per-role accounting", "", "```json", json.dumps({k: v.get("breakdown", {}) for k, v in present.items()}, indent=2), "```", ""]
    report = "\n".join(lines)
    (base / "comparison.md").write_text(report)
    (base / "comparison.json").write_text(json.dumps(present, indent=2))
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
