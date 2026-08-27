"""Round 5: recall under growth — accuracy when facts must survive in memory.

The environment serves each module's spec EXACTLY ONCE (read-once, then
destroyed). Ground truth is recomputed from the XL generator's formulas.

5A retention: ~3k-token docs, 40 modules (~140k total, fits the window).
   single: fetch all 40 with NO storage tools, then submit one table from
           memory -> per-fact score, bucketed by fetch position.
   swarm:  each worker fetches its one spec and submits its row immediately.

5B wall: ~7k-token docs (~280k total, exceeds the 200k window).
   single: may record facts incrementally (best case) — measures coverage
           at the moment the context wall kills it.
   swarm:  same incremental recording, one module per worker.
"""
import concurrent.futures as cf
import json
import sys
import threading
import time
from pathlib import Path

import anthropic

from orchestrator2 import PRICE, RUNS, cost
from generate_xl import DOMAINS

MODEL = "claude-haiku-4-5-20251001"
N = 40
FIELDS = ["base_rate", "tier_threshold", "tier_factor",
          "weekend_rate", "holiday_rate", "min_fee"]


def module_facts(i):
    weekend = round(0.10 + (i % 5) * 0.01, 2)
    return {
        "base_rate": round(0.03 + (i % 7) * 0.005, 4),
        "tier_threshold": 200 + 25 * (i % 9),
        "tier_factor": round(0.80 - (i % 4) * 0.05, 2),
        "weekend_rate": weekend,
        "holiday_rate": round(weekend + 0.07, 2),
        "min_fee": round(1.0 + (i % 3) * 0.5, 2),
    }


GROUND = {DOMAINS[i]: module_facts(i) for i in range(N)}
MODULES = [DOMAINS[i] for i in range(N)]


def build_doc(module, facts, target_chars):
    spec = (f"=== {module} fee engine: OPERATING SPECIFICATION ===\n"
            f"BASE_RATE = {facts['base_rate']}\n"
            f"TIER_THRESHOLD = {facts['tier_threshold']}\n"
            f"TIER_FACTOR = {facts['tier_factor']}\n"
            f"WEEKEND_RATE = {facts['weekend_rate']}\n"
            f"HOLIDAY_RATE = {facts['holiday_rate']}\n"
            f"MIN_FEE = {facts['min_fee']}\n"
            f"=== END OF CONSTANTS ===\n\n")
    pad = []
    j = 0
    while sum(len(p) for p in pad) + len(spec) < target_chars:
        j += 1
        pad.append(
            f"Operational note {j} for the {module} engine: settlement records "
            f"are reconciled nightly against the ledger snapshot, and any "
            f"variance is routed to the exceptions queue for manual review by "
            f"the regional operations team before the next billing cycle "
            f"begins. Historical archives are retained per policy addendum "
            f"{module}-{j:03d} and are unrelated to fee computation.\n")
    return spec + "".join(pad)


class SpecService:
    """Read-once spec store shared by all agents in a condition."""
    def __init__(self, target_chars):
        self.docs = {m: build_doc(m, GROUND[m], target_chars) for m in MODULES}
        self.consumed = []            # fetch order
        self.lock = threading.Lock()

    def fetch(self, module):
        with self.lock:
            if module not in self.docs:
                return f"ERROR: spec for '{module}' is GONE — it was already fetched once and destroyed." \
                    if module in MODULES else f"ERROR: unknown module '{module}'"
            doc = self.docs.pop(module)
            self.consumed.append(module)
            return doc


class ToolAgent:
    """Minimal tool loop; same caching/retry mechanics as the bench Worker."""
    def __init__(self, system, tools, handlers, label, terminal=("done",)):
        self.system = system
        self.tools = tools
        self.handlers = handlers
        self.label = label
        self.terminal = set(terminal)
        self.client = anthropic.Anthropic()
        self.usage = {"input": 0, "output": 0, "cache_read": 0, "cache_write": 0}

    def _call(self, messages):
        for m in messages:
            if isinstance(m["content"], list):
                for b in m["content"]:
                    if isinstance(b, dict):
                        b.pop("cache_control", None)
        last = messages[-1]["content"]
        if isinstance(last, list) and last and isinstance(last[-1], dict):
            last[-1]["cache_control"] = {"type": "ephemeral"}
        delay = 2.0
        for attempt in range(6):
            try:
                return self.client.messages.create(
                    model=MODEL, max_tokens=4000,
                    system=[{"type": "text", "text": self.system,
                             "cache_control": {"type": "ephemeral"}}],
                    tools=self.tools, messages=messages)
            except (anthropic.RateLimitError, anthropic.InternalServerError,
                    anthropic.APIConnectionError):
                if attempt == 5:
                    raise
                time.sleep(delay)
                delay = min(delay * 2, 60)

    def run(self, brief, max_turns, chaos_rate=0.0, rng=None):
        messages = [{"role": "user", "content": [{"type": "text", "text": brief}]}]
        turns, exhausted, stopped_by = 0, False, None
        self.killed = False
        while turns < max_turns:
            try:
                resp = self._call(messages)
            except anthropic.BadRequestError as e:
                if any(s in str(e).lower() for s in ("too long", "context", "maximum")):
                    exhausted = True
                    print(f"[{self.label}] CONTEXT EXHAUSTED at turn {turns}", flush=True)
                    break
                raise
            turns += 1
            u = resp.usage
            self.usage["input"] += u.input_tokens
            self.usage["output"] += u.output_tokens
            self.usage["cache_read"] += getattr(u, "cache_read_input_tokens", 0) or 0
            self.usage["cache_write"] += getattr(u, "cache_creation_input_tokens", 0) or 0
            calls = [b for b in resp.content if b.type == "tool_use"]
            if not calls:
                break
            messages.append({"role": "assistant", "content": resp.content})
            results, stop = [], False
            for tu in calls:
                fn = self.handlers.get(tu.name)
                out = fn(tu.input or {}) if fn else f"ERROR: unknown tool {tu.name}"
                results.append({"type": "tool_result", "tool_use_id": tu.id,
                                "content": out})
                if tu.name in self.terminal:
                    stop, stopped_by = True, tu.name
            messages.append({"role": "user", "content": results})
            if stop:
                break
            if chaos_rate and rng and rng.random() < chaos_rate:
                self.killed = True
                print(f"[{self.label}] KILLED by chaos at turn {turns}", flush=True)
                break
        return {"turns": turns, "context_exhausted": exhausted,
                "killed": self.killed,
                "stopped_by": stopped_by, "usage": dict(self.usage)}


def score_rows(rows):
    """rows: list of dicts with module + FIELDS. Returns per-module correct counts."""
    per_module = {}
    for row in rows:
        m = str(row.get("module", "")).strip()
        if m not in GROUND:
            continue
        ok = 0
        for f in FIELDS:
            try:
                if abs(float(row.get(f)) - GROUND[m][f]) < 1e-6:
                    ok += 1
            except (TypeError, ValueError):
                pass
        per_module[m] = max(ok, per_module.get(m, 0))
    return per_module


FETCH_TOOL = {"name": "fetch_spec",
              "description": "Fetch a module's operating specification document. Each spec can be fetched EXACTLY ONCE — it is destroyed after being served.",
              "input_schema": {"type": "object",
                               "properties": {"module": {"type": "string"}},
                               "required": ["module"]}}

ROWS_SCHEMA = {"type": "array", "items": {
    "type": "object",
    "properties": {**{"module": {"type": "string"}},
                   **{f: {"type": "number"} for f in FIELDS}},
    "required": ["module"] + FIELDS}}

SUBMIT_TOOL = {"name": "submit_table",
               "description": "Submit the final consolidated table of constants for ALL modules. Call exactly once, at the end.",
               "input_schema": {"type": "object",
                                "properties": {"rows": ROWS_SCHEMA},
                                "required": ["rows"]}}

RECORD_TOOL = {"name": "record_facts",
               "description": "Durably record extracted constants for one or more modules. Call as often as you like; this is your only storage.",
               "input_schema": {"type": "object",
                                "properties": {"rows": ROWS_SCHEMA},
                                "required": ["rows"]}}

DONE_TOOL = {"name": "done", "description": "Call when finished.",
             "input_schema": {"type": "object", "properties": {
                 "summary": {"type": "string"}}, "required": []}}

SYSTEM = ("You are a data-extraction agent. Specs are served read-once: each "
          "fetch_spec succeeds only the first time for a module. Constants must "
          "be reported EXACTLY as written in the spec.")


def condition_a_single():
    svc = SpecService(12000)
    submitted = []
    agent = ToolAgent(
        SYSTEM, [FETCH_TOOL, SUBMIT_TOOL],
        {"fetch_spec": lambda a: svc.fetch(str(a.get("module", ""))),
         "submit_table": lambda a: (submitted.extend(a.get("rows", [])), "received")[1]},
        "5A-single", terminal=("submit_table",))
    brief = (f"Modules, in this exact order: {', '.join(MODULES)}.\n\n"
             "Fetch every module's spec (each can be fetched only once, and you "
             "have NO storage tools — the constants must survive in your working "
             "memory). After you have fetched ALL 40, call submit_table exactly "
             "once with all 40 rows (module + the 6 constants each).")
    t0 = time.monotonic()
    res = agent.run(brief, max_turns=60)
    per_module = score_rows(submitted)
    order = {m: k for k, m in enumerate(svc.consumed)}
    buckets = [[] for _ in range(5)]
    for m in MODULES:
        if m in order:
            buckets[min(order[m] * 5 // max(len(order), 1), 4)].append(per_module.get(m, 0))
    return {"condition": "5A_single", "wall_seconds": round(time.monotonic() - t0, 1),
            "facts_correct": sum(per_module.values()), "facts_total": N * 6,
            "modules_fetched": len(svc.consumed), "rows_submitted": len(submitted),
            "position_buckets_pct": [round(100 * sum(b) / (6 * len(b)), 1) if b else None
                                     for b in buckets],
            **res, "est_cost_usd": cost(res["usage"])}


def condition_a_swarm():
    svc = SpecService(12000)
    lock = threading.Lock()
    all_rows = []
    t0 = time.monotonic()

    def one(module):
        rows = []
        agent = ToolAgent(
            SYSTEM, [FETCH_TOOL, SUBMIT_TOOL],
            {"fetch_spec": lambda a: svc.fetch(str(a.get("module", ""))),
             "submit_table": lambda a: (rows.extend(a.get("rows", [])), "received")[1]},
            f"5A-w:{module}", terminal=("submit_table",))
        res = agent.run(f"Fetch the spec for module '{module}' (read-once), then "
                        f"call submit_table with that single module's row.",
                        max_turns=6)
        with lock:
            all_rows.extend(rows)
        return res

    with cf.ThreadPoolExecutor(max_workers=12) as ex:
        results = list(ex.map(one, MODULES))
    per_module = score_rows(all_rows)
    usage = {k: sum(r["usage"][k] for r in results) for k in PRICE}
    return {"condition": "5A_swarm", "wall_seconds": round(time.monotonic() - t0, 1),
            "facts_correct": sum(per_module.values()), "facts_total": N * 6,
            "turns": sum(r["turns"] for r in results), "usage": usage,
            "est_cost_usd": cost(usage)}


def condition_b(mode):
    svc = SpecService(28000)
    lock = threading.Lock()
    recorded = []

    def record(a):
        with lock:
            recorded.extend(a.get("rows", []))
        return "recorded"

    t0 = time.monotonic()
    if mode == "single":
        agent = ToolAgent(
            SYSTEM, [FETCH_TOOL, RECORD_TOOL, DONE_TOOL],
            {"fetch_spec": lambda a: svc.fetch(str(a.get("module", ""))),
             "record_facts": record, "done": lambda a: "ok"},
            "5B-single")
        brief = (f"Modules, in this exact order: {', '.join(MODULES)}.\n\n"
                 "For EACH module: fetch its spec (read-once), then IMMEDIATELY "
                 "call record_facts with its 6 constants before fetching the next "
                 "one — recording is your only storage. Call done after all 40.")
        res = agent.run(brief, max_turns=100)
        results = [res]
    else:
        def one(module):
            agent = ToolAgent(
                SYSTEM, [FETCH_TOOL, RECORD_TOOL, DONE_TOOL],
                {"fetch_spec": lambda a: svc.fetch(str(a.get("module", ""))),
                 "record_facts": record, "done": lambda a: "ok"},
                f"5B-w:{module}")
            return agent.run(f"Fetch the spec for module '{module}' (read-once), "
                             f"record its 6 constants with record_facts, then done.",
                             max_turns=6)
        with cf.ThreadPoolExecutor(max_workers=12) as ex:
            results = list(ex.map(one, MODULES))

    per_module = score_rows(recorded)
    usage = {k: sum(r["usage"][k] for r in results) for k in PRICE}
    return {"condition": f"5B_{mode}", "wall_seconds": round(time.monotonic() - t0, 1),
            "facts_correct": sum(per_module.values()), "facts_total": N * 6,
            "modules_recorded": len(per_module),
            "modules_fetched": len(svc.consumed),
            "context_exhausted": any(r.get("context_exhausted") for r in results),
            "turns": sum(r["turns"] for r in results), "usage": usage,
            "est_cost_usd": cost(usage)}


if __name__ == "__main__":
    which = sys.argv[1]  # a_single | a_swarm | b_single | b_swarm
    fn = {"a_single": condition_a_single, "a_swarm": condition_a_swarm,
          "b_single": lambda: condition_b("single"),
          "b_swarm": lambda: condition_b("swarm")}[which]
    result = fn()
    out = RUNS / f"result_r5_{which}.json"
    out.write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2), flush=True)
    print(f"written: {out}", flush=True)
