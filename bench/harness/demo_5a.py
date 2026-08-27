"""Re-run 5A-single with full logging so the run is inspectable."""
import json
import time
from pathlib import Path

from round5 import (SpecService, ToolAgent, GROUND, MODULES, FIELDS,
                    FETCH_TOOL, SUBMIT_TOOL, SYSTEM, score_rows)
from orchestrator2 import RUNS, cost

svc = SpecService(12000)
submitted = []
fetch_log = []


def fetch(a):
    module = str(a.get("module", ""))
    fetch_log.append({"module": module, "at": round(time.monotonic() - t0, 1)})
    return svc.fetch(module)


def submit(a):
    submitted.extend(a.get("rows", []))
    return "received"


brief = (f"Modules, in this exact order: {', '.join(MODULES)}.\n\n"
         "Fetch every module's spec (each can be fetched only once, and you "
         "have NO storage tools — the constants must survive in your working "
         "memory). After you have fetched ALL 40, call submit_table exactly "
         "once with all 40 rows (module + the 6 constants each).")

t0 = time.monotonic()
agent = ToolAgent(SYSTEM, [FETCH_TOOL, SUBMIT_TOOL],
                  {"fetch_spec": fetch, "submit_table": submit},
                  "5A-demo", terminal=("submit_table",))
res = agent.run(brief, max_turns=60)

per_module = score_rows(submitted)
report = {
    "brief": brief,
    "turns": res["turns"],
    "wall_seconds": round(time.monotonic() - t0, 1),
    "est_cost_usd": cost(res["usage"]),
    "peak_context_tokens_approx": res["usage"]["cache_write"],
    "fetch_order": [f["module"] for f in fetch_log],
    "facts_correct": sum(per_module.values()),
    "facts_total": len(MODULES) * 6,
    "submitted_rows": submitted,
    "ground_truth": GROUND,
}
out = RUNS / "demo_5a_full_log.json"
out.write_text(json.dumps(report, indent=2))

# printable verification: submitted vs truth, row by row
print(f"turns={res['turns']}  wall={report['wall_seconds']}s  "
      f"peak_context≈{report['peak_context_tokens_approx']:,} tok  "
      f"cost=${report['est_cost_usd']}")
print(f"score: {report['facts_correct']}/{report['facts_total']}\n")
print(f"{'module':16s} {'submitted (from memory)':44s} verdict")
for row in submitted[:100]:
    m = row.get("module", "?")
    truth = GROUND.get(m, {})
    vals = " ".join(str(row.get(f)) for f in FIELDS)
    ok = all(abs(float(row.get(f, -1)) - truth.get(f, -2)) < 1e-6 for f in FIELDS) if truth else False
    print(f"{m:16s} {vals:44s} {'ALL 6 CORRECT' if ok else 'MISMATCH'}")
