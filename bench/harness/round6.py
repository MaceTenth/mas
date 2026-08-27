"""Round 6: hard extraction, near-ceiling context, under chaos.

- Docs ~4.4k tokens x 40 => single-agent context rides to ~180k (~95% of window).
- Facts are adversarial: derivations, unit conversions, explicit decoys,
  scattered one-per-paragraph among noise. Extraction itself can fail.
- Chaos: per-turn kill probability for every agent. Specs are read-once, so a
  spec fetched by an agent that dies before recording is PERMANENTLY lost.
- Both sides get identical tools: fetch_spec, record_facts (durable),
  list_recorded, done. Recorded facts survive crashes; contexts do not.
- Multiple seeded trials per condition; per-trial and aggregate reporting.
"""
import concurrent.futures as cf
import json
import random
import sys
import threading
import time

from round5 import ToolAgent, MODULES, FIELDS, FETCH_TOOL, RECORD_TOOL, DONE_TOOL
from orchestrator2 import PRICE, RUNS, cost

CHAOS = 0.05
DOC_CHARS = 17600
SINGLE_TRIALS = 4
SWARM_TRIALS = 3
MAX_SINGLE_TURNS = 120
MAX_WORKER_ATTEMPTS = 3

LIST_TOOL = {"name": "list_recorded",
             "description": "List module names whose facts are already durably recorded.",
             "input_schema": {"type": "object", "properties": {}, "required": []}}

SYSTEM = ("You are a data-extraction agent. Specs are served READ-ONCE: a fetch "
          "destroys the spec, and if you crash before recording, those facts are "
          "permanently unrecoverable. Facts are stated indirectly — derived values, "
          "unit conversions, and REJECTED proposals that must NOT be reported. "
          "Record the values actually in force, exactly.")


def trial_facts(seed):
    rng = random.Random(seed)
    facts, decoys = {}, {}
    for m in MODULES:
        f = {
            "base_rate": round(rng.uniform(0.011, 0.089), 4),
            "tier_threshold": rng.randrange(110, 970),
            "tier_factor": round(rng.uniform(0.51, 0.94), 2),
            "weekend_rate": round(rng.uniform(0.05, 0.29), 2),
            "holiday_rate": round(rng.uniform(0.05, 0.33), 2),
            "min_fee": round(rng.randrange(60, 940, 2) / 100, 2),
        }
        d = {"tier_factor": round(min(0.99, f["tier_factor"] + 0.07), 2),
             "weekend_rate": round(f["weekend_rate"] + 0.04, 2)}
        facts[m], decoys[m] = f, d
    return facts, decoys


def fact_paragraphs(m, f, d):
    old_rate = round(f["base_rate"] - 0.0025, 4)
    return [
        f"Rate committee minute for {m}: last cycle's base rate of {old_rate} was "
        f"raised by 25 basis points (0.0025) at the January sitting; the base rate "
        f"in force is the sum of those two figures.",
        f"Billing systems bulletin for {m}: the tier threshold stands at "
        f"{f['tier_threshold'] * 100} cents; downstream systems must convert to "
        f"whole currency units before applying tier logic.",
        f"Pricing board resolution for {m}: a proposal to move TIER_FACTOR to "
        f"{d['tier_factor']} was REJECTED after review; the factor remains "
        f"{f['tier_factor']} until further notice.",
        f"Correction notice for {m}: contrary to the widely circulated draft memo "
        f"citing a weekend surcharge of {d['weekend_rate']}, the surcharge "
        f"actually in force is {f['weekend_rate']}.",
        f"Holiday pipeline appendix for {m}: the holiday surcharge is "
        f"{f['holiday_rate']} and applies exclusively through the holiday "
        f"settlement pipeline.",
        f"Fee floor memorandum for {m}: the minimum fee is defined as exactly "
        f"twice the base floor, and the base floor for this engine is "
        f"{round(f['min_fee'] / 2, 2)}.",
    ]


def build_hard_doc(m, f, d):
    noise = (f"Routine note {{j}} for the {m} engine: settlement records are "
             f"reconciled nightly against the ledger snapshot, variances route to "
             f"the exceptions queue for regional review, and archives follow "
             f"policy addendum {m}-{{j:03d}}, none of which affects fees.\n\n")
    parts = [f"=== {m} engine: OPERATIONS DIGEST (constants are stated within "
             f"the prose below, one per relevant notice) ===\n\n"]
    fps = fact_paragraphs(m, f, d)
    j = 0
    fi = 0
    while sum(len(p) for p in parts) < DOC_CHARS:
        j += 1
        parts.append(noise.format(j=j))
        if j % 4 == 2 and fi < len(fps):     # facts buried at intervals
            parts.append(fps[fi] + "\n\n")
            fi += 1
    while fi < len(fps):
        parts.append(fps[fi] + "\n\n")
        fi += 1
    return "".join(parts)


class HardService:
    def __init__(self, seed):
        self.truth, decoys = trial_facts(seed)
        self.docs = {m: build_hard_doc(m, self.truth[m], decoys[m]) for m in MODULES}
        self.consumed = set()
        self.recorded = {}           # module -> row (last write wins)
        self.lock = threading.Lock()

    def fetch(self, a):
        m = str(a.get("module", ""))
        with self.lock:
            if m not in self.docs:
                return (f"ERROR: spec for '{m}' is GONE — fetched once and destroyed."
                        if m in MODULES else f"ERROR: unknown module '{m}'")
            self.consumed.add(m)
            return self.docs.pop(m)

    def record(self, a):
        with self.lock:
            for row in a.get("rows", []):
                m = str(row.get("module", "")).strip()
                if m in MODULES:
                    self.recorded[m] = row
        return "recorded"

    def listing(self, a):
        with self.lock:
            return ", ".join(sorted(self.recorded)) or "(nothing recorded yet)"

    def score(self):
        ok, wrong = 0, []
        for m, row in self.recorded.items():
            for f in FIELDS:
                try:
                    if abs(float(row.get(f)) - self.truth[m][f]) < 1e-6:
                        ok += 1
                    else:
                        wrong.append(f"{m}.{f}={row.get(f)} (truth {self.truth[m][f]})")
                except (TypeError, ValueError):
                    wrong.append(f"{m}.{f} unparseable")
        lost = sorted(self.consumed - set(self.recorded))
        return {"facts_correct": ok, "facts_total": len(MODULES) * 6,
                "extraction_errors": wrong, "modules_recorded": len(self.recorded),
                "modules_lost_permanently": lost}


TOOLS = [FETCH_TOOL, RECORD_TOOL, LIST_TOOL, DONE_TOOL]


def run_single_trial(seed):
    svc = HardService(seed)
    rng = random.Random(seed * 31 + 7)
    handlers = {"fetch_spec": svc.fetch, "record_facts": svc.record,
                "list_recorded": svc.listing, "done": lambda a: "ok"}
    brief = (f"Modules, in this exact order: {', '.join(MODULES)}.\n\n"
             "Extract and record the 6 constants (base_rate, tier_threshold, "
             "tier_factor, weekend_rate, holiday_rate, min_fee) for ALL 40 modules. "
             "Specs are read-once; recorded facts survive crashes; facts you have "
             "fetched but not yet recorded are permanently lost if you crash. "
             "Your batching strategy is up to you. If you are a replacement after "
             "a crash, call list_recorded first. Call done when all recoverable "
             "modules are recorded.")
    turns = kills = 0
    t0 = time.monotonic()
    usage = {k: 0 for k in PRICE}
    while turns < MAX_SINGLE_TURNS:
        agent = ToolAgent(SYSTEM, TOOLS, handlers, f"6-single-s{seed}")
        res = agent.run(brief, max_turns=MAX_SINGLE_TURNS - turns,
                        chaos_rate=CHAOS, rng=rng)
        turns += res["turns"]
        for k in PRICE:
            usage[k] += res["usage"][k]
        if res["killed"] or res["context_exhausted"]:
            kills += 1
            continue
        break
    out = svc.score()
    out.update({"seed": seed, "kills": kills, "turns": turns,
                "wall_seconds": round(time.monotonic() - t0, 1),
                "est_cost_usd": cost(usage)})
    return out


def run_swarm_trial(seed):
    svc = HardService(seed)
    t0 = time.monotonic()
    usages = []

    def one(idx_module):
        idx, module = idx_module
        rng = random.Random(seed * 7919 + idx)
        handlers = {"fetch_spec": svc.fetch, "record_facts": svc.record,
                    "list_recorded": svc.listing, "done": lambda a: "ok"}
        kills = 0
        for attempt in range(MAX_WORKER_ATTEMPTS):
            agent = ToolAgent(SYSTEM, TOOLS, handlers, f"6-w:{module}")
            res = agent.run(
                f"Extract and record the 6 constants for module '{module}' only "
                f"(fetch_spec is read-once; record_facts is durable; a crash "
                f"between fetch and record loses the module forever). If "
                f"fetch_spec says GONE, check list_recorded and call done.",
                max_turns=6, chaos_rate=CHAOS, rng=rng)
            usages.append(res["usage"])
            if res["killed"]:
                kills += 1
                continue
            break
        return kills

    with cf.ThreadPoolExecutor(max_workers=12) as ex:
        kill_counts = list(ex.map(one, enumerate(MODULES)))

    usage = {k: sum(u[k] for u in usages) for k in PRICE}
    out = svc.score()
    out.update({"seed": seed, "kills": sum(kill_counts),
                "wall_seconds": round(time.monotonic() - t0, 1),
                "est_cost_usd": cost(usage)})
    return out


if __name__ == "__main__":
    which = sys.argv[1]  # single | swarm
    trials = []
    if which == "single":
        for s in range(1, SINGLE_TRIALS + 1):
            print(f"--- single trial seed={s} ---", flush=True)
            trials.append(run_single_trial(s))
            print(json.dumps({k: v for k, v in trials[-1].items()
                              if k != "extraction_errors"}), flush=True)
    else:
        for s in range(1, SWARM_TRIALS + 1):
            print(f"--- swarm trial seed={s} ---", flush=True)
            trials.append(run_swarm_trial(s))
            print(json.dumps({k: v for k, v in trials[-1].items()
                              if k != "extraction_errors"}), flush=True)
    scores = [t["facts_correct"] for t in trials]
    summary = {"condition": f"round6_{which}", "chaos_rate": CHAOS,
               "trials": len(trials), "scores": scores,
               "mean_score": round(sum(scores) / len(scores), 1),
               "min_score": min(scores), "max_score": max(scores),
               "total_cost_usd": round(sum(t["est_cost_usd"] for t in trials), 3),
               "detail": trials}
    (RUNS / f"result_r6_{which}.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps({k: v for k, v in summary.items() if k != "detail"},
                     indent=2), flush=True)
