"""Deterministic tally for demo 3 — runs as a mas worker (ExecWorker) after every vote and
the debate have landed. Holds the planted ground truth, which the reviewers never see
(this file lives in the mas package, not in the reviewed repository).

usage: tally.py <compartment-dir>
writes: result/tally.json, result/summary.md
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

TRUTH = {
    "bug": True,
    "where": "get_profile: the cache key is user_id alone — include_private is not part of the key",
    "scenario": "get_profile('u1', include_private=True) fills the cache; a public get_profile('u1') then returns email/phone/billing (or the reverse: the account page misses private fields for 5 minutes)",
    # a vote 'matches' when it points at the key / the private flag / the leak
    "keywords": ["key", "include_private", "private", "leak", "same cache", "cache entry", "public"],
}


def matches_truth(v: dict) -> bool:
    blob = " ".join(str(v.get(k, "")) for k in ("location", "scenario", "fix")).lower()
    return bool(v.get("bug")) and any(k in blob for k in TRUTH["keywords"])


def load(p: Path) -> dict | None:
    try:
        return json.loads(p.read_text())
    except Exception:
        return None


def main(root: Path) -> int:
    votes_dir, out = root / "votes", root / "result"
    out.mkdir(exist_ok=True)
    votes = []
    for p in sorted(votes_dir.glob("vote-*.json")):
        v = load(p) or {}
        parts = p.stem.split("-")                      # vote-3-codex
        votes.append({"id": p.stem, "harness": parts[-1] if len(parts) >= 3 else "?", "bug": bool(v.get("bug")),
                      "severity": v.get("severity", "?"), "location": str(v.get("location", ""))[:90],
                      "confidence": v.get("confidence"), "matches_truth": matches_truth(v)})
    n = len(votes)
    yes = sum(1 for v in votes if v["bug"])
    found = sum(1 for v in votes if v["matches_truth"])
    by_h: dict = {}
    for v in votes:
        h = by_h.setdefault(v["harness"], {"n": 0, "found": 0})
        h["n"] += 1; h["found"] += int(v["matches_truth"])
    majority_bug = yes * 2 > n
    majority_found = found * 2 > n
    vote_correct = majority_bug == TRUTH["bug"] and majority_found
    single = votes[0] if votes else None                # one sample = "a single agent's opinion"

    debate = load(root / "final.json")
    debate_ok = bool(debate) and matches_truth(debate)

    tally = {"truth": {"bug": TRUTH["bug"], "where": TRUTH["where"]}, "votes": votes,
             "majority": {"bug_yes": yes, "n": n, "located_the_bug": found, "correct": vote_correct},
             "by_harness": by_h, "single_sample": {"id": single["id"], "correct": single["matches_truth"]} if single else None,
             "debate": {"present": bool(debate), "correct": debate_ok, "location": (debate or {}).get("location"),
                        "agreed_with": (debate or {}).get("agreed_with"), "overruled": (debate or {}).get("overruled")}}
    (out / "tally.json").write_text(json.dumps(tally, indent=2))

    def mark(b): return "✓" if b else "✗"
    lines = ["# Debate or vote — PR #142", "",
             f"**Planted truth:** {TRUTH['where']}.", f"**Failing scenario:** {TRUTH['scenario']}.", "",
             f"## Votes — {n} independent reviewers, no shared context", "",
             "| vote | harness | bug? | severity | location (as written) | found it |", "|---|---|---|---|---|---|"]
    for v in votes:
        lines.append(f"| {v['id']} | {v['harness']} | {'YES' if v['bug'] else 'no'} | {v['severity']} | {v['location']} | {mark(v['matches_truth'])} |")
    lines += ["", f"**Majority:** bug YES {yes}/{n} · located the real bug {found}/{n} → **{'correct' if vote_correct else 'incorrect'}**",
              "**By harness:** " + " · ".join(f"{h} {d['found']}/{d['n']}" for h, d in by_h.items()), "",
              "## Debate — one adjudicator reading all votes", ""]
    if debate:
        lines += [f"- verdict: bug {'YES' if debate.get('bug') else 'no'} · {debate.get('severity', '?')} · {str(debate.get('location', ''))[:120]}",
                  f"- agreed with: {debate.get('agreed_with')} · overruled: {debate.get('overruled')}",
                  f"- reasoning: {str(debate.get('reasoning', ''))[:400]}", f"- **{'correct' if debate_ok else 'incorrect'}**"]
    else:
        lines.append("- final.json missing — the debate item did not land")
    lines += ["", "## Scorecard", "", "| method | correct |", "|---|---|",
              f"| one sample ({single['id'] if single else '-'}) | {mark(single['matches_truth']) if single else '-'} |",
              f"| majority vote of {n} | {mark(vote_correct)} |",
              f"| debate (adjudicator over {n} votes) | {mark(debate_ok)} |", "",
              "_Words are voted, actions are gated: the schema gate only checked that each verdict was well-formed; the truth came from independent samples._"]
    (out / "summary.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1]).resolve()))
