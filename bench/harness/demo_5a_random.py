"""5A-single again, but with pattern-free randomized constants.

Kills the confound that the regular generator values (0.03, 0.035, ...) could
be pattern-inferred instead of recalled.
"""
import json
import random
import time

import round5
from round5 import (SpecService, ToolAgent, MODULES, FIELDS,
                    FETCH_TOOL, SUBMIT_TOOL, SYSTEM, score_rows)
from orchestrator2 import RUNS, cost

rng = random.Random(123)
for m in MODULES:
    round5.GROUND[m] = {
        "base_rate": round(rng.uniform(0.011, 0.089), 4),
        "tier_threshold": rng.randrange(110, 970),
        "tier_factor": round(rng.uniform(0.51, 0.94), 2),
        "weekend_rate": round(rng.uniform(0.05, 0.29), 2),
        "holiday_rate": round(rng.uniform(0.05, 0.33), 2),
        "min_fee": round(rng.uniform(0.6, 9.4), 2),
    }

svc = SpecService(12000)   # rebuilds docs from the mutated GROUND
submitted = []

brief = (f"Modules, in this exact order: {', '.join(MODULES)}.\n\n"
         "Fetch every module's spec (each can be fetched only once, and you "
         "have NO storage tools — the constants must survive in your working "
         "memory). After you have fetched ALL 40, call submit_table exactly "
         "once with all 40 rows (module + the 6 constants each).")

t0 = time.monotonic()
agent = ToolAgent(SYSTEM, [FETCH_TOOL, SUBMIT_TOOL],
                  {"fetch_spec": lambda a: svc.fetch(str(a.get("module", ""))),
                   "submit_table": lambda a: (submitted.extend(a.get("rows", [])), "received")[1]},
                  "5A-rand", terminal=("submit_table",))
res = agent.run(brief, max_turns=60)

per_module = score_rows(submitted)
correct = sum(per_module.values())
print(f"RANDOMIZED constants: score {correct}/240  turns={res['turns']}  "
      f"wall={round(time.monotonic()-t0,1)}s  peak_context≈{res['usage']['cache_write']:,} tok  "
      f"cost=${cost(res['usage'])}")
wrong = []
for row in submitted:
    m = row.get("module")
    truth = round5.GROUND.get(m, {})
    for f in FIELDS:
        try:
            if abs(float(row.get(f)) - truth[f]) >= 1e-6:
                wrong.append(f"{m}.{f}: submitted {row.get(f)} truth {truth[f]}")
        except (TypeError, ValueError, KeyError):
            wrong.append(f"{m}.{f}: unparseable {row.get(f)!r}")
print(f"errors: {len(wrong)}")
for w in wrong[:12]:
    print(" ", w)
(RUNS / "demo_5a_random.json").write_text(json.dumps(
    {"score": correct, "total": 240, "turns": res["turns"],
     "errors": wrong, "submitted_rows": submitted,
     "ground_truth": round5.GROUND}, indent=2))
