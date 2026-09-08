# mas — a multi-agent environment

> A single agent is a swarm with N = 1. You never choose whether to build the MAS — only N.

`mas` is the environment from the lecture, as a CLI: a **durable board** with atomic
claims and expiring leases, **git-worktree compartments**, interchangeable **workers**
(Claude Code, Codex, Anthropic/Gemini/OpenAI API loops, or any headless CLI — alone or as a mixed fleet),
a **verification gate** that never trusts a worker's "done", a **restartable orchestrator** with
backoff, model escalation and a circuit breaker, and an **append-only event log** with
views for humans.

```
pip install -e .            # in the project venv
mas demo list               # the demos and what each one shows
mas demo run 1              # one fleet: 4 Claude workers on 8 items (resets ~/mas-demo, no flags needed)
mas demo run 2              # mixed fleet: Claude + Codex on the same repo, 4 items each
mas demo run 3              # debate or vote: no tests — 8 independent reviewers vote on a PR, one adjudicator debates, a script tallies
mas demo run 4              # many eyes: a harder PR with 4 planted bugs — one reviewer vs majority vs union vs debate
mas demo run 4 --fleet claude   # same, on haiku/sonnet alternating when Codex is unavailable
mas demo run 5              # advice as context: Mini alone vs GPT-5.5 alone vs Mini + a mandatory private-context adviser
mas demo run 6              # chaos recovery: dead lease, bad output, crash, timeout, retries, breaker, evidence report
mas watch                   # from a second terminal, inside ~/mas-demo
```

Demo runs reset their destination. If `~/mas-demo` contains a different layout such as Demo 5's multi-variant results,
preserve it with `--dir ~/mas-demo-6`, or explicitly replace it with `--force`.

Each demo writes every flag it needs into the project's `.mas/config.json`, so inside the demo
directory a plain `mas run` (after a Ctrl-C, say) continues with the same settings. Your own
project: `mas init`, `mas add …` or `mas plan "goal"` or `mas import-issues owner/repo`, then `mas run`.

## The live view

`mas run` in a terminal draws a live dashboard (8 fps) — a materialized view over the
board's append-only event log, so `mas watch` shows exactly the same thing from any other
process sharing the board:

- **header** — the whole configuration: workers, concurrency, lease, heartbeat, turn budget,
  timeout, backoff curve, breaker threshold, escalation tiers per worker
- **progress** — verified / running / parked, attempts, turns, cost, elapsed
- **board** — one row per item: spinner while leased, `⏳ backoff 12s`, `⛔ parked`, attempt
  `2/3`, the worker+model, the lease countdown with a ♥ that lights on every heartbeat, and
  what the worker is doing right now (its latest tool call)
- **workers in flight** — per live worker: item, model, current tool call, elapsed, tool calls so far
- **event log** — every board write as it happens, colored by subsystem: `＋ added`, `🔒 claimed`,
  `🧱 worktree ready`, `🚀 dispatched (⬆ escalated)`, `⚙ Edit src/lru.py`, `🤖 worker finished`,
  `🛡 gate running`, `✅ VERIFIED` / `❌ REJECTED — worker claimed success`, `📦 landed · commit`,
  `🏁 DONE`, `↻ requeued · backoff 6.4s · next: sonnet`, `⛔ PARKED — circuit breaker open`,
  `⏰ lease expired`, `↩ lease handed back`, `💡 lesson`

Worker activity comes from `claude -p --output-format stream-json` (and `codex exec --json`),
so you see each tool call the moment it happens. Not a TTY (CI, `| tee`, tests) → `--plain`
line logs automatically; `--quiet` hides the tool-call lines. `mas status`, `mas events`,
`mas show`, `mas dashboard` use the same colors.

## The five boxes → files

| box | file | tools it implements |
|---|---|---|
| board | `mas/board.py` | queue + atomic claim + leases + breaker + append-only log (3 · 4 · 6 · 9) |
| compartments / store | `mas/workspace.py` | worktree per attempt, idempotent merge, commit (1 · 2 · 4) |
| workers | `mas/workers.py` | `claude -p`, `codex exec`, API loop — same contract (2) |
| gate | `mas/verify.py` | `cmd:` / `schema:` / `human` / `none` (8) |
| orchestrator | `mas/orchestrator.py` | budgets, backoff, escalation, breaker, restart-from-board (5 · 6 · 7) |
| views | `mas/views.py` | status, show, dashboard, events, lessons (9) |
| decomposer | `mas/plan.py` | goal → validated items via `claude -p --json-schema` (1) |
| GitHub layer | `mas/github.py` | issues → items; verdicts → close/comment |

## Plugging in any harness

`mas` never integrates with a harness's internals. A worker is a black box: it gets a **prompt**
(the brief plus the check that will be run) and an **isolated directory**, it exits, and whatever it
changed in that directory is the result. The gate re-runs the check, so nothing a worker says is
trusted. That is the whole contract (`workers.py`):

```
run(prompt, cwd, model, max_turns, timeout_s, on_activity) -> WorkerResult
```

So any CLI agent qualifies if it (1) runs non-interactively, (2) accepts a prompt, (3) works in a given
directory, (4) exits. Describe it in `.mas/config.json` — no code:

```
mas harnesses                 # built-ins, configured harnesses, presets
mas harnesses add hermes      # preset → .mas/config.json   (also: gemini, opencode, aider)
mas run --workers claude,codex,hermes
```

```json
"harnesses": {
  "mybot": { "cmd": ["mybot", "--headless", "--prompt", "{prompt}", "--model", "{model}"],
             "prompt_via": "arg", "summary": "stdout_tail", "activity": "lines" } },
"models":    { "mybot": ["small-model", "big-model"] }
```

Placeholders: `{prompt}` `{prompt_file}` `{cwd}` `{model}` `{max_turns}` `{out_file}`. The prompt can go
in as an argument, on stdin, or as a file; the summary comes from the stdout tail or a file the harness
writes; `activity` turns its stdout (or a field of its JSONL events) into live tool-call lines in the
view. Model tiers per kind give escalation on retry, `worker_pref` pins an item to a kind, and the
gate, leases, breaker, worktrees and event log are identical for every kind — that is what makes the
harness a config value rather than an architecture decision.

What else is pluggable: the **board** is an interface (claim · heartbeat · complete · fail · expire ·
log) with SQLite as the reference implementation and GitHub Issues as a mirror; the **gate** is a shell
command or schema; the **store** is a git worktree per attempt; the **views** are queries over the log.

## Demo 5: advice as private context

Demo 5 tests whether a stronger model can improve a fast executor by changing its context without taking over
its work. It runs the same temporal authorization-engine task in four fresh repositories:

1. `gpt-5.4-mini-2026-03-17` alone
2. the same Mini executor with the private packet placed directly in its task context
3. the same Mini executor with a mandatory read-only consultation from `gpt-5.5-2026-04-23`
4. `gpt-5.5-2026-04-23` alone

Only the executor receives repository write and check tools. The advised executor must inspect the task and consult
before its first edit: the harness rejects `edit_file`, `write_file`, and `done` until a consultation succeeds. The
adviser receives the task, selected repository snapshots, and the organization-private Cerulean-7 conflict profile,
then returns text advice. The direct-context arm receives the identical packet in Mini's initial API input, without
an adviser tool. The profile is never copied into an executor repository, and the other solo conditions do not receive
it. The adviser cannot edit files or declare the item complete.

Mini uses medium reasoning in all three Mini variants; GPT-5.5 uses high reasoning as adviser and alone. All variants have
one attempt, one worker slot, the same 24-turn executor budget, and the same external 50-case quality oracle. The
oracle reports 30 public-contract cases and 20 private-profile cases separately without leaking expected values to
the worker. At the end `~/mas-demo/comparison.md` reports quality by section, board status, wall time, tokens,
estimated API cost, executor turns, successful/attempted adviser calls, and per-role accounting.

```bash
export OPENAI_API_KEY=...       # use a live key from your environment; never commit it
mas demo run 5
# faster iteration:
mas demo run 5 --variants small-alone,small-direct-context,advised
```

The direct-context arm is the retrieval control: comparing it with the advised arm asks whether the adviser adds useful
reasoning beyond merely delivering the missing packet. This is still one fixed task; repeat across seeds and tasks before
claiming a general adviser advantage.

In the first four-arm run, direct-context Mini and advised Mini both scored 50/50. Direct context took 60.1 seconds and
$0.0407; advice took 69.1 seconds and $0.0757. Mini alone scored 20/50, while GPT-5.5 alone scored 48/50 in 111.2 seconds
for $0.4744. On this task, the measured gain came from routing the missing context; the extra adviser reasoning added no
quality over giving Mini the same packet directly.

## Demo 6: recovery under intentional failure

Demo 6 is a deterministic, zero-API-cost chaos run. Its workers are ordinary headless subprocess harnesses, but they
fail on cue so the outcome does not depend on hoping a model behaves badly. The first verified item writes `PLAN.json`;
MAS validates it, rejects one malformed generated entry, and dynamically adds the recovery graph to the board.

The run injects a dead orchestrator lease with partial work, a worker that confidently writes the wrong answer, a
non-zero process exit, a worker that exceeds its time budget, and an irrecoverable item. In parallel, a healthy worker
runs longer than its two-second lease while heartbeats renew ownership. The environment then demonstrates:

- lease expiry and restart from durable SQLite state;
- fresh worktree compartments, retry backoff, and escalation from `fast-agent` to `recovery-agent`;
- independent command/schema gates that reject false success;
- serialized, scoped, and idempotent landing on the shared Git main branch;
- dependencies, `deps=settled`, a circuit breaker with its failed compartment retained, and a run-last observer;
- durable lesson transfer, mixed harnesses, atomic claims, and the append-only WAL event log.

The observer derives `result/recovery.md` and `result/recovery.json` from the database and filesystem evidence. One item
finishes parked by design: recovery means bounding an irrecoverable fault and allowing explicitly settled dependents to
continue, not relabeling every failure as success. The report explicitly maps its evidence back to all nine tools in the
lecture: bounded contexts, bulkheads, the queue, idempotency/leases, timeouts/retries/backoff, the breaker, restart from
the board, verification gates, and event-sourced views.

```bash
mas demo run 6
less ~/mas-demo/result/recovery.md
sqlite3 ~/mas-demo/.mas/board.db \
  "select seq,item_id,kind,data from events order by seq"
```

## Items that spawn items

An item whose `meta.spawn` names a JSON file it landed (a planner's `PLAN.json`, a reviewer's
`REVIEW.json`) puts that file's entries on the board when it finishes — before it is marked done, so a
`run_last` scorer cannot slip in between. Entries need `title`, `brief`, `check`; `id`, `merge_paths`,
`worker`, `model`, `depends_on` (by raw id, prefixed id, or title) are optional and `defaults` fill the
rest. Templates under `after` are added with `depends_on` = the whole batch, which is how a review
follows the doers and a final review follows the fixes. Bad entries are skipped and logged; nothing a
model writes is trusted past the schema. A `run_last` item (a deterministic scorer, say) is claimable only when everything else has settled.

## Your own task, from the CLI

Nothing in the demos is special: they only call the board API. The same shapes are available
from the command line. Demo 4 ("many eyes") written by hand:

```bash
cd my-project && mas init
mas harnesses add codex                 # optional: any extra harness

# 8 independent reviewers — the bulkhead pattern. {i} {n} {kind} {id} {persona} {slug} are substituted.
mas fanout 8 "Review PR #207 as {persona}" --fleet claude,codex --slug review \
  --persona "a skeptical maintainer" --persona "a security auditor" \
  --persona "a QA engineer" --persona "a new team member" \
  --brief-file review-brief.md --schema findings.schema.json \
  --check "schema:votes/{id}.json" --merge "votes/{id}.json"

# one adjudicator, on a stronger model, once every review has settled (done or parked)
mas add "Consolidate the reviews" --worker claude --model sonnet --brief-file consolidate.md \
  --check schema:final.json --schema consolidated.schema.json --merge final.json \
  --depends-on 'review-*' --deps settled

# a deterministic step as a worker: any script is a harness
mas harnesses add tally --cmd python my_tally.py "{cwd}"     # (or edit .mas/config.json)
mas add "Tally" --worker tally --check "cmd:test -s result/summary.md" --merge result/summary.md \
  --depends-on 'review-*,consolidate-the-reviews' --deps settled

mas run                                 # or: mas run --workers claude,codex,tally
```

`mas add` takes `--brief`/`--brief-file`/stdin, `--check` (`cmd:` · `schema:` + `--schema file` · `human` ·
`none`), `--merge` (repeatable), `--worker` (built-in or any configured harness), `--model`,
`--depends-on` (ids or globs), `--deps done|settled`, `--priority`, `--max-attempts`, `--meta k=v`.
`mas plan "goal"` asks a model to decompose a goal into items; `mas import-issues owner/repo` turns
GitHub issues into items and mirrors verdicts back.

## Items

Items can depend on each other (`depends_on`): an item is claimable only when every dependency is
`done`. Demo 3 uses it for votes → debate → tally. An item's `meta.model` pins a model for that item
(the adjudicator runs on sonnet while the votes run on haiku). A pinned model applies to the first attempt; retries escalate through the kind's tiers.

An item is the four decisions: **the cut** (one item), **the contract** (`brief`, `merge_paths`),
**the check** (`cmd:…`, `schema:…`, `human`), **the view** (what lands and what's logged).

```
mas add "Fix failing tests in src/lru.py" \
  --brief "Tests in tests/test_lru.py define correct LRU behaviour…" \
  --check "cmd:python -m pytest tests/test_lru.py -q" --merge src/lru.py --worker codex
```

## Workers: requirements

- `claude` — Claude Code CLI on PATH, logged in (or `ANTHROPIC_API_KEY`). The item's check command is auto-allowed so the worker can self-verify.
- `codex` — Codex CLI ≥ 0.150 on PATH, logged in (`codex exec --sandbox workspace-write --json --ephemeral`).
  Workers run with `codex_overrides` (default: reasoning effort `high`, personal MCP servers disabled; demo 2 uses `medium`).
- `api` — `ANTHROPIC_API_KEY` in the environment; a harness-free tool loop (cheapest per task).
- `gemini` — `GEMINI_API_KEY` in the environment (`pip install google-genai`); the same tool loop on Gemini
  function calling. Default tiers `gemini-2.5-flash` → `gemini-2.5-pro`; the 3.5 Flash family works too
  (cost is estimated only for models with a known list price; tokens are always reported). Measured:
  a demo-1 fix in ~9 s for ~$0.005 on 2.5-flash.
- `openai` — `OPENAI_API_KEY` in the environment (`openai>=2`); a Responses API tool loop with exact token and
  estimated list-price accounting. Set `openai_advisor_model` to expose the bounded, read-only `ask_advisor` tool;
  `openai_min_advice_calls` can enforce a pre-edit consultation, and a package-owned adviser context file can supply
  information unavailable to the executor. Demo 5 uses all three. The default OpenAI tiers are GPT-5.4 Mini → GPT-5.5.

## Reliability behaviour

- a worker dies → its lease expires → the item reopens → another worker takes it (as the next attempt, in a fresh compartment)
- a worker is stuck → its attempt hits the turn/time budget → rejected → retried with a stronger model
- an item fails `max_attempts` times → **parked** with evidence (`mas show <id>`) → `mas unpark <id>`;
  a lease that expires on the final attempt parks too — nothing is ever re-queued past `max_attempts`
- a worker "finishes" after losing its lease → its verified files still land (idempotent), but the board is left
  to the attempt that now owns the item (`done_without_lease` in the log)
- **Ctrl-C / SIGTERM** is a graceful stop: live workers are killed (whole process groups), their leases are handed
  back with the attempt refunded, `mas run` exits 130, and the next run continues immediately
- **SIGKILL / power cut** is fine too: every state change is a board write — rerun and the leases expire
- heartbeats renew leases at ≤ lease/3, so a healthy worker never loses its item
- `mas supervise` restarts `mas run --forever`; `--install-launchd` writes a LaunchAgent

## Verified (2026-09-03, real workers)

| test | result |
|---|---|
| demo, 4 Claude workers (Haiku, escalation to Sonnet) | 8/8 verified and committed in 2m24s, ≈$0.78 |
| circuit breaker (`cmd:exit 1` check) | attempt 1 haiku rejected → backoff → attempt 2 sonnet rejected → parked with evidence → `mas unpark` |
| crash: SIGKILL mid-run, rerun | leased items expired and were retaken; 8/8, 42 tests green; no spurious lease loss while alive |
| mixed fleet `--workers claude,api` | round-robin dispatch, both items verified, ≈$0.09 |
| GitHub layer (`mas import-issues`, `--github`) | issue → item → verified → issue closed with the verdict comment |
| Codex worker (codex-cli 0.153, `--sandbox workspace-write --json`) | item verified, landed and committed in 32s; tool calls streamed live |
| `mas demo run 2` — mixed fleet Claude + Codex, same repo | 8/8 first attempt in 81s, 4 items each, both streams of tool calls live, both landing verified commits on one main |
| `mas demo run 4` — many eyes, 4 planted bugs, Claude + Codex | 10/10 items first attempt in 8m38s, ≈$1.41. Every one of the 8 reviewers found all 4 planted bugs (recall 100% for a single reviewer, so this PR did not separate one view from many). The value showed up elsewhere: 5/8 flagged the checked-in webhook secret, 4/8 found an unplanted idempotency-key bug in renewals, 2/8 an API-contract bug; the sonnet adjudicator kept 7 findings and dropped 1 unreachable one |
| `mas demo run 3` — debate or vote on a PR with no tests | 4 Claude reviewers independently found the planted cache-key leak (4/4, all "critical"); the sonnet adjudicator agreed with all four; the tally script landed the scorecard. Codex's backend returned 404 for the whole run, so its 4 votes tripped the breaker with evidence and the debate/tally proceeded on the settled votes |
| `mas demo run 6` — deterministic recovery chaos | 18/18 recovery patterns proven from SQLite evidence in about 21 seconds at zero API cost; 13 items done, one intentionally parked after its breaker opened |
| unit tests, no LLM | `python -m pytest tests/test_mas.py -q` — exclusive claims, leases, breaker, release, idempotent merge, fake-worker orchestrator runs, API loops, demo wiring, gate, escalation, crash-resume, graceful stop |
