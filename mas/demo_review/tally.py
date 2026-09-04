"""Deterministic tally for demo 4 (many eyes) — runs as a mas worker after every review and
the adjudication have settled. Holds the planted ground truth, which reviewers never see
(this file lives in the mas package, not in the reviewed repository).

usage: tally.py <compartment-dir>
writes: result/tally.json, result/summary.md

A finding is attributed to the planted bug whose keywords it hits most (location words weigh
double). Findings that hit nothing are 'unmatched' — a false positive, or a real issue we did
not plant; the summary lists them so a human can tell which.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

BUGS = [
    {"id": "B1", "name": "webhook replay double-credits the account",
     "where": "webhooks.handle_webhook — the provider redelivers the same event id until 2xx; events_seen is never consulted, so every redelivery adds amount_cents again",
     "loc": ["handle_webhook", "webhooks.py", "events_seen"],
     "kw": ["idempot", "event id", "event_id", "duplicate", "redeliver", "re-deliver", "replay", "double-credit", "double credit", "credited twice", "twice", "again", "retries the same"]},
    {"id": "B2", "name": "export_invoices has no authorization check",
     "where": "api.export_invoices — get_invoice and list_invoices call _authorize; the bulk export does not, so any user can export any account's invoices",
     "loc": ["export_invoices", "api.py"],
     "kw": ["authoriz", "_authorize", "ownership", "any account", "other account", "another account", "idor", "access control", "any user", "another user", "forbidden", "permission"]},
    {"id": "B3", "name": "line totals truncate cents",
     "where": "billing.line_total_cents — int(unit_price * quantity * 100) truncates: 19.99 * 3 * 100 = 5996.999… → 5996 instead of 5997",
     "loc": ["line_total_cents", "invoice_total_cents", "billing.py"],
     "kw": ["truncat", "round", "float", "int(", "5996", "5997", "19.99", "precision", "off by one cent", "cent"]},
    {"id": "B4", "name": "renew() marks the subscription active when the charge failed",
     "where": "billing.renew + provider.charge — charge() returns None after exhausting retries or on a declined card; renew() stores it and sets status='active' regardless",
     "loc": ["renew", "charge(", "provider.py", "last_charge"],
     "kw": ["returns none", "return none", "none", "swallow", "silent", "failed charge", "charge fail", "declined", "active even", "active regardless", "marks", "raise", "exhaust"]},
]


def attribute(f: dict) -> tuple[str | None, int]:
    text = " ".join(str(f.get(k, "")) for k in ("title", "location", "scenario", "fix")).lower()
    best, score = None, 0
    for b in BUGS:
        loc_hits = sum(1 for k in b["loc"] if k.lower() in text)
        kw_hits = sum(1 for k in b["kw"] if k.lower() in text)
        if kw_hits == 0:                 # being in the same file is not the same bug
            continue
        s = 2 * loc_hits + kw_hits
        if s > score:
            best, score = b["id"], s
    return (best if score >= 2 else None), score


def load(p: Path):
    try:
        return json.loads(p.read_text())
    except Exception:
        return None


def review(v: dict) -> dict:
    found, unmatched = {}, []
    for f in (v or {}).get("findings", []) or []:
        if not isinstance(f, dict):
            continue
        bid, score = attribute(f)
        if bid:
            found.setdefault(bid, str(f.get("title", ""))[:80])
        else:
            unmatched.append(str(f.get("title", ""))[:80])
    return {"found": found, "unmatched": unmatched}


def main(root: Path) -> int:
    out = root / "result"
    out.mkdir(exist_ok=True)
    ids = [b["id"] for b in BUGS]
    rows = []
    for p in sorted((root / "votes").glob("vote-*.json"), key=lambda q: int(q.stem.split("-")[1])):
        parts = p.stem.split("-")
        r = review(load(p) or {})
        rows.append({"id": p.stem, "harness": parts[2] if len(parts) > 2 else "?", "model": parts[3] if len(parts) > 3 else "",
                     "found": sorted(r["found"]), "n_found": len(r["found"]), "unmatched": r["unmatched"], "recall": len(r["found"]) / len(ids)})
    n = len(rows)
    per_bug = {bid: sum(1 for r in rows if bid in r["found"]) for bid in ids}
    union = sorted({b for r in rows for b in r["found"]})
    majority = sorted(b for b, k in per_bug.items() if k * 2 > n)
    recalls = [r["recall"] for r in rows] or [0]
    by_group: dict = {}
    for r in rows:
        g = by_group.setdefault(f"{r['harness']}{(' ' + r['model']) if r['model'] else ''}", [])
        g.append(r["recall"])
    debate = load(root / "final.json")
    dr = review(debate or {})
    tally = {"bugs": [{"id": b["id"], "name": b["name"], "found_by": per_bug[b["id"]], "of": n} for b in BUGS],
             "reviewers": rows,
             "single": {"mean_recall": sum(recalls) / len(recalls), "best": max(recalls), "worst": min(recalls)},
             "union": {"found": union, "recall": len(union) / len(ids)},
             "majority": {"found": majority, "recall": len(majority) / len(ids)},
             "by_group": {g: sum(v) / len(v) for g, v in by_group.items()},
             "debate": {"present": bool(debate), "found": sorted(dr["found"]), "recall": len(dr["found"]) / len(ids), "unmatched": dr["unmatched"]}}
    (out / "tally.json").write_text(json.dumps(tally, indent=2))

    def pct(x): return f"{round(100 * x)}%"
    L = ["# Many eyes — PR #207", "", f"**Planted bugs ({len(ids)}):**", ""]
    for b in BUGS:
        L.append(f"- **{b['id']} · {b['name']}** — {b['where']}")
    L += ["", f"## Reviewers — {n} independent, no shared context", "",
          "| reviewer | found | recall | unmatched findings (false positive or unplanted) |", "|---|---|---|---|"]
    for r in rows:
        who = r["id"] + (f" ({r['model']})" if r["model"] else "")
        L.append(f"| {who} | {' '.join(r['found']) or '—'} | {pct(r['recall'])} | {'; '.join(r['unmatched']) or '—'} |")
    L += ["", "**Per bug — how many reviewers found it:** " + " · ".join(f"{b}: {k}/{n}" for b, k in per_bug.items()),
          "**By group:** " + " · ".join(f"{g} {pct(v)}" for g, v in tally["by_group"].items()), "",
          "## Debate — one adjudicator consolidating all reviews", ""]
    if debate:
        L += [f"- kept {len((debate or {}).get('findings', []))} findings → planted bugs found: {' '.join(dr['found']) or '—'} ({pct(tally['debate']['recall'])})",
              f"- unmatched (false positive or unplanted): {'; '.join(dr['unmatched']) or '—'}",
              f"- dropped: {len((debate or {}).get('dropped', []))} · reasoning: {str((debate or {}).get('reasoning', ''))[:300]}"]
    else:
        L.append("- final.json missing — the debate item did not land")
    L += ["", "## Scorecard", "", "| method | planted bugs found |", "|---|---|",
          f"| one reviewer, average | {pct(tally['single']['mean_recall'])} |",
          f"| one reviewer, best / worst | {pct(tally['single']['best'])} / {pct(tally['single']['worst'])} |",
          f"| majority of {n} (found by more than half) | {pct(tally['majority']['recall'])} |",
          f"| union of {n} (found by anyone) | {pct(tally['union']['recall'])} |",
          f"| debate (adjudicator over {n} reviews) | {pct(tally['debate']['recall'])} |", "",
          "_Independent views add recall; the adjudicator's job is precision. The schema gate only checked shape — the truth came from many eyes._"]
    (out / "summary.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1]).resolve()))
