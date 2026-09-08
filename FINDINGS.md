# What we did, and what we found

*A running record of the `mas` project: the thesis, the experiments, the numbers, and the lessons. Dates are 2026-08-25 to 2026-09-03.*

## The thesis

A multi-agent system is not "more agents". It is infrastructure: a durable board, isolated compartments, a
verification gate that never trusts a worker, and an append-only log. Once that exists, the number of agents
is a config value. A single agent is a swarm with N = 1.

Two facts underneath everything: a model call is stateless, so "the agent" is the transcript, and whoever holds
the transcript holds the agent. And a single context hits three walls: the window (inputs that do not fit),
the crash (one process, all work lost), and the backlog (one thread cannot clear many tasks in parallel).

## What we built

**Benchmarks (rounds 1 to 7).** A fair harness on the Anthropic API: same model, prompt and tools for a
single agent and a swarm; equal aggregate budgets; the orchestrator scores with pytest, never the model.
Findings: accuracy ties at equal budget; the swarm wins wall-clock (1.5 to 2.3 times), crash resilience, and the
window wall; the single agent wins cost and, on repeated-structure work, accuracy. A relay chain was the only
topology that destroyed work. Memory is a cliff, not a slope.

**The lecture** (`lecture/build_lecture.js`, 32 slides). Four laws of complex systems; what an agent is
("same model, same code, only the context changed"); the reveal that there are no agents, only context; why the
obsession with agents that talk fails; nine tools from distributed systems; the environment; three cases; the
two dials; design choices.

**The `mas` tool** (`mas/`). Board (SQLite, atomic claims, leases, heartbeats, backoff, breaker, events), git
worktree per attempt with idempotent landing, workers (Claude Code, Codex, Gemini API, Anthropic API, OpenAI
Responses API, or any headless CLI via config), the gate, a restartable orchestrator with model escalation, items that depend on items,
items that spawn items, a live terminal view materialized from the log, a GitHub Issues mirror, and six live demos.
Thirty-plus unit tests drive the orchestrator with fake workers so no invariant depends on a model.

## The demos and their numbers

| demo | setup | result |
|---|---|---|
| 1 · one fleet | 4 Claude Haiku workers fix 8 buggy modules | 8/8 verified in about 2.5 minutes for under $1 |
| 2 · mixed fleet | Claude and Codex share one repo, 4 items each | 8/8 in 81 s; commits from both on one main |
| 3 · debate or vote | 8 reviewers vote on a PR with one planted bug, one adjudicator | every reviewer found it; the adjudicator agreed; Codex's backend was down that hour and its 4 votes parked with evidence |
| 4 · many eyes | 8 reviewers, 4 planted bugs in 5 files | every reviewer found all 4; the extra value was an unplanted real bug found by 4 of 8 and a checked-in secret flagged by 5 of 8 |
| 5a · planner + doers (retired) | sonnet plans and reviews, haiku implements, vs one agent | team 42/44 in 64 min for $9.82; single sonnet 44/44 in 6 min for $1.69; single haiku 43/44 in 5 min for $0.33 |
| old 6 · export backlog (retired; number reused) | 32 generated vendor formats, checks from data, 8 Gemini Flash doers vs one sonnet | stopped before completion; the team had 27 of 32 parsers landed at about 4 minutes, one parked |
| 5b · advice as private context (4 three-arm runs + 1 four-arm control) | GPT-5.4 Mini alone vs direct private context vs a mandatory read-only GPT-5.5 consultation vs GPT-5.5 alone | advised Mini scored 50/50 in all 5; in the four-arm run direct-context Mini also scored 50/50 and was faster/cheaper than advice (60 s/$0.0407 vs 69 s/$0.0757); GPT-5.5 alone scored 46–49/50; Mini alone scored 20, 20, 20, 47, and 20 |
| 6 · recovery under intentional failure | deterministic headless workers inject a dead lease, false success, process crash, timeout, permanent failure, and malformed spawned item | 18/18 recovery patterns proven from 193 ordered SQLite events in about 21 s at $0; 13 items done and one intentionally parked; the run exposed and fixed two real shared-store defects |

The original planner/doer demo 5a and the export-backlog prototype formerly numbered 6 were removed from the tool on
2026-09-03; their findings stay. The new Demo 6 is the deterministic recovery lab and is unrelated to that prototype.
Demo 5b is a new, narrower adviser experiment and should not be conflated with the retired decomposition experiment.
Its first dependency-resolver design was not a valid adviser test: all three variants scored 24/24 and the advised
Mini made zero adviser calls. That result motivated the current harder task, enforced consultation checkpoint, and
adviser-only information condition.

## Main findings

1. **The gate is the product.** Every demo that worked did so because the orchestrator re-ran the check itself.
   Workers claimed success and were wrong on several occasions; nothing unverified ever landed.

2. **Decomposition has a price, and a one-window task pays it without collecting the benefit.** Retired demo 5a is the
   cleanest evidence: the same spec, one strong agent finished in 6 minutes for under $2 with a perfect score;
   the team took ten times longer and six times the money and scored lower. Splitting work only pays when the
   work breaks a wall.

3. **The contract can be wrong, and the loop cannot see it.** In retired demo 5a the planner wrote one incorrect test
   assertion. Six correct implementations of the module were rejected by it, costing 40 of the 64 minutes and
   about $4. The reviewer, who had written the test, diagnosed "never implemented" and never suspected its own
   contract. The review loop catches implementation errors and is blind to contract errors when the contract's
   author is the reviewer. Checks should come from data, fixtures, or a reference, never from a model's prose.

4. **The brief is part of the contract.** An adjudicator told to expect "8 reviews" when only 4 existed spent its
   entire turn budget searching git branches and polling for the missing ones. Never promise state the
   environment cannot guarantee.

5. **Independent views add recall; the adjudicator adds precision.** In demo 4 every reviewer found the planted
   bugs, so the vote could not beat one reviewer on recall. The value showed elsewhere: a real unplanted bug found
   by half the reviewers, and an adjudicator that kept 7 findings and dropped 1 after checking the code.

6. **Cheap models are fast and good enough when the check is real.** Gemini 2.5 Flash fixed demo-1 modules in
   about 9 seconds each for half a cent apiece, gate-verified. In demo 6 eight Flash workers landed 27 of 32
   verified parsers in about four minutes.

7. **Reliability comes from the environment, not the model.** Crash-resume (SIGKILL mid-run, rerun, leases expire,
   work continues), graceful stop (Ctrl-C releases leases and refunds attempts), the breaker (park after N failures
   with evidence), heartbeats, per-attempt compartments, and idempotent landing were all exercised and each caught
   a real bug during development: a heartbeat longer than the lease, a shared worktree between a stale and a fresh
   attempt, an exhausted item re-queued past its limit, a race between spawning an item and recording its issue.

8. **GitHub Issues are a mirror, not a scheduler.** They have no atomic claim and they rate-limit you, so the board
   schedules and Issues show humans what happened: one issue per item, a comment per step, close with the verdict.

9. **Every harness is a black box behind one contract.** A worker receives a prompt and a directory, exits, and
   whatever it changed is gated. Claude Code, Codex, Gemini, the raw API, or any headless CLI described in config
   all fit, which is what makes the vendor a config value.

10. **Advice can be a context route, not a delegation layer.** Across four runs the Mini executor plus a mandatory
    GPT-5.5 consultation passed all 50 authorization cases every time. GPT-5.5 alone implemented the public contract
    every time but missed one to four private-profile cases; at the median, the advised architecture was 1.8× faster
    and 5.2× cheaper. Mini alone stalled without editing in three runs and reached 47/50 in the fourth. This measures
    reliability on one fixed task with intentionally different information access, not general model superiority.
    A fifth, four-arm run added the retrieval control: Mini given the same packet directly also scored 50/50, in 60.1
    seconds for $0.0407, versus 69.1 seconds and $0.0757 with the adviser. Here the adviser added no quality beyond
    delivering the missing context, which is an important negative result for the stronger claim about advisory reasoning.

11. **Fault injection turns reliability claims into executable evidence.** The new Demo 6 deliberately created a dead
    lease, false success, process crash, timeout, and permanent failure. The system recovered every recoverable item,
    parked the irrecoverable one, and let an explicitly settled run-last observer finish. Building the demo exposed two
    genuine shared-store bugs: concurrent Git commits could race on the index, and Git collapsed wholly untracked output
    directories so directory-prefix merges landed nothing. Serializing the narrow landing boundary and requesting
    `--untracked-files=all` fixed both; the final observer proved 18/18 patterns from the SQLite event history.

## What comes next

Run the retired export-backlog experiment to completion with a fair deadline for the single agent, and make the
team task hard enough on the window wall to separate one view from many on recall, not only on findings outside
the plan. Demo 5b now includes a direct-context control (Mini receives the private packet without an adviser); run all
four arms across several private profiles and policy fixtures. That separates retrieval value from adviser reasoning
and tests whether the result generalizes beyond one fixed task.
