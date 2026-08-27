"""Round 7: replicate De Marzo et al. (Science Advances 2026) majority-following
on Haiku 4.5 — then show the infrastructure escape hatch.

Part A (response function): controlled majority fraction f, raw shuffled peer
list, fit majority force beta per group size N via Curie-Weiss law
P(follow) = (1 + tanh(beta * m)) / 2, m = 2f - 1.

Part B (dynamics, emergent): the paper's coordination game — each agent sees
the raw unaggregated list of all peers' current choices. Synchronous rounds
(paper uses async single-agent updates; noted deviation for wall-clock).

Part C (dynamics, infrastructure): identical, but agents see ONE aggregated
count line — a task-board summary — instead of the raw list.

Consensus metric: magnetization |m| = |n_A - n_B| / N -> 1.
"""
import concurrent.futures as cf
import json
import math
import random
import sys
import time

import anthropic

from orchestrator2 import PRICE, RUNS, cost

MODEL = "claude-haiku-4-5-20251001"
WORDS = ("kula", "vopa")
CONCURRENCY = 12

client = anthropic.Anthropic()
usage_total = {k: 0 for k in PRICE}
import threading
_ulock = threading.Lock()

SYSTEM = ("You are one agent in a group coordination game. Every agent picks one "
          "of two words. The whole group wins only if EVERYONE ends up on the "
          "same word. Neither word is better - the only goal is to match the "
          "group. Reply with exactly one word: your choice.")


def ask(prompt, rng):
    delay = 2.0
    for attempt in range(6):
        try:
            r = client.messages.create(
                model=MODEL, max_tokens=16,
                system=SYSTEM,
                messages=[{"role": "user", "content": prompt},
                          {"role": "assistant", "content": "I choose:"}])
            with _ulock:
                usage_total["input"] += r.usage.input_tokens
                usage_total["output"] += r.usage.output_tokens
                usage_total["cache_read"] += getattr(r.usage, "cache_read_input_tokens", 0) or 0
                usage_total["cache_write"] += getattr(r.usage, "cache_creation_input_tokens", 0) or 0
            text = "".join(b.text for b in r.content if b.type == "text").lower()
            for w in WORDS:
                if w in text:
                    return w
            print(f"[unparseable] {text[:80]!r}", flush=True)
            return None
        except (anthropic.RateLimitError, anthropic.InternalServerError,
                anthropic.APIConnectionError):
            if attempt == 5:
                raise
            time.sleep(delay)
            delay = min(delay * 2, 60)


def peer_list_prompt(choices, rng):
    shuffled = list(choices)
    rng.shuffle(shuffled)
    return (f"The current choices of the other {len(choices)} agents, "
            f"in no particular order:\n{', '.join(shuffled)}\n\nYour choice:")


def board_prompt(choices):
    a = sum(1 for c in choices if c == WORDS[0])
    b = len(choices) - a
    return (f"Board summary of the other {len(choices)} agents: "
            f"{a} currently choose '{WORDS[0]}', {b} choose '{WORDS[1]}'.\n\nYour choice:")


# ---------------- Part A: response function ----------------
def part_a():
    NS = [10, 25, 50, 100, 200]
    FS = [0.55, 0.6, 0.7, 0.8, 0.9]
    SAMPLES = 30
    jobs = []
    for N in NS:
        for f in FS:
            for k in range(SAMPLES):
                jobs.append((N, f, k))

    def one(job):
        N, f, k = job
        rng = random.Random(hash(job) & 0xFFFFFFFF)
        maj = rng.choice(WORDS)                     # counterbalance word bias
        minr = WORDS[1] if maj == WORDS[0] else WORDS[0]
        n_maj = round(f * (N - 1))
        choices = [maj] * n_maj + [minr] * (N - 1 - n_maj)
        ans = ask(peer_list_prompt(choices, rng), rng)
        return (N, f, None if ans is None else (ans == maj))

    with cf.ThreadPoolExecutor(max_workers=CONCURRENCY) as ex:
        results = list(ex.map(one, jobs))

    out = {}
    for N in NS:
        pts = []
        for f in FS:
            vals = [r[2] for r in results if r[0] == N and r[1] == f and r[2] is not None]
            pts.append({"f": f,
                        "p_follow": round(sum(vals) / len(vals), 3) if vals else None,
                        "n": len(vals)})
        # fit beta: P = (1 + tanh(beta*m))/2, m = 2f-1, max likelihood grid
        best_b, best_ll = 0.0, -1e18
        for bi in range(0, 3001):
            b = bi * 0.01
            ll = 0.0
            for f in FS:
                m = 2 * f - 1
                p = min(max((1 + math.tanh(b * m)) / 2, 1e-9), 1 - 1e-9)
                vals = [r[2] for r in results if r[0] == N and r[1] == f and r[2] is not None]
                ll += sum(math.log(p) if v else math.log(1 - p) for v in vals)
            if ll > best_ll:
                best_ll, best_b = ll, b
        out[N] = {"beta": round(best_b, 2), "curve": pts}
        print(f"[A] N={N}: beta={best_b:.2f}  " +
              " ".join(f"f={p['f']}→{p['p_follow']}" for p in pts), flush=True)
    return out


# ---------------- Parts B & C: dynamics ----------------
def dynamics(N, mode, trial, max_rounds=25):
    rng = random.Random(1000 * N + trial)
    state = [WORDS[i % 2] for i in range(N)]
    rng.shuffle(state)
    traj = []

    def m_of(st):
        a = sum(1 for c in st if c == WORDS[0])
        return abs(2 * a / N - 1)

    for rnd in range(max_rounds):
        traj.append(round(m_of(state), 3))
        if m_of(state) == 1.0:
            break

        def upd(i):
            others = state[:i] + state[i + 1:]
            prompt = (peer_list_prompt(others, random.Random(rng.random()))
                      if mode == "emergent" else board_prompt(others))
            ans = ask(prompt, rng)
            return ans if ans else state[i]

        with cf.ThreadPoolExecutor(max_workers=CONCURRENCY) as ex:
            state = list(ex.map(upd, range(N)))

    final = m_of(state)
    traj.append(round(final, 3))
    print(f"[{mode}] N={N} trial={trial}: m={traj}  consensus={final == 1.0}", flush=True)
    return {"N": N, "mode": mode, "trial": trial, "consensus": final == 1.0,
            "final_m": round(final, 3), "rounds": len(traj) - 1, "trajectory": traj}


if __name__ == "__main__":
    which = sys.argv[1]  # a | b | c
    t0 = time.monotonic()
    if which == "a":
        result = {"part": "A_response_function", "beta_by_N": part_a()}
    elif which == "b":
        runs = []
        for N in (10, 50):
            for t in (1, 2):
                runs.append(dynamics(N, "emergent", t))
        runs.append(dynamics(200, "emergent", 1))
        result = {"part": "B_dynamics_emergent", "runs": runs}
    else:
        runs = [dynamics(200, "board", 1), dynamics(200, "board", 2)]
        result = {"part": "C_dynamics_board", "runs": runs}
    result["wall_seconds"] = round(time.monotonic() - t0, 1)
    result["usage"] = usage_total
    result["est_cost_usd"] = cost(usage_total)
    (RUNS / f"result_r7_{which}.json").write_text(json.dumps(result, indent=2))
    print(json.dumps({k: v for k, v in result.items() if k not in ("beta_by_N", "runs")},
                     indent=2), flush=True)
