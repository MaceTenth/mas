"""Assemble docs/journey-trip.md from the captured evidence of the trip run: the planner prompt and raw
answer, the board before/during/after, the full event journal, the WAL files, git history, the outputs."""
import json, re, sqlite3, subprocess, sys, time
from pathlib import Path

S = Path(__file__).resolve().parent / "journey-trip-evidence"   # the captured evidence of the run
PROJ = Path.home() / "mas-trip"
OUT = Path(__file__).resolve().parent / "journey-trip.md"
GOAL = "Plan a 10-day trip from Israel to Japan in November for two people, budget $6,000"


def read(p, default=""):
    try:
        return Path(p).read_text()
    except OSError:
        return default


def fence(text, lang=""):
    return f"```{lang}\n{text.rstrip()}\n```\n"


def sh(cmd, cwd=PROJ):
    r = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    return (r.stdout + r.stderr).rstrip()


plan = json.loads(read(S / "last_plan.json", "{}"))
raw_items = (plan.get("raw") or {}).get("items", [])
before = read(S / "before.txt")
prompt_block = before.split("=== the exact prompt a worker will receive for item 'flights' ===")[-1].strip()
tables_block = before.split("=== items table")[0].replace("=== sqlite: tables and journal mode ===", "").strip()
items_block = before.split("=== items table (one row per task) ===")[-1].split("=== events so far")[0].strip()
events_before = before.split("=== events so far (the journal begins) ===")[-1].split("=== the exact prompt")[0].strip()

con = sqlite3.connect(f"file:{PROJ / '.mas' / 'board.db'}?mode=ro", uri=True)
con.row_factory = sqlite3.Row
ev = [dict(r) for r in con.execute("select seq, ts, item_id, kind, data from events order by seq")]
t0 = min(e["ts"] for e in ev if e["kind"] == "claimed") if any(e["kind"] == "claimed" for e in ev) else ev[0]["ts"]
items = [dict(r) for r in con.execute("select id, status, attempts, worker_pref, depends_on, merge_paths, verdict from items order by created_at")]
lessons = [dict(r) for r in con.execute("select ts, item_id, text from lessons order by seq")]
kinds = {}
for e in ev:
    kinds[e["kind"]] = kinds.get(e["kind"], 0) + 1


def rel(ts):
    d = ts - t0
    return f"{'+' if d >= 0 else ''}{d:6.1f}s"


def short(d, n=100):
    s = json.dumps(d, ensure_ascii=False)
    return s if len(s) <= n else s[: n - 1] + "…"


journal_lines = []
for e in ev:
    d = json.loads(e["data"] or "{}")
    if e["kind"] == "activity":
        summary = f"{d.get('tool')} {str(d.get('arg', ''))[:70]}"
    elif e["kind"] in ("verified", "rejected"):
        summary = f"passed={d.get('passed')} · {str(d.get('detail', '')).strip().splitlines()[-1][:70] if d.get('detail') else ''}"
    elif e["kind"] == "worker_finished":
        summary = f"claims_ok={d.get('ok')} · {d.get('turns')} turns · ${d.get('cost_usd')} · {d.get('seconds')}s"
    elif e["kind"] == "merged":
        summary = f"landed={d.get('landed')} commit={d.get('commit')}"
    elif e["kind"] == "dispatched":
        summary = f"{d.get('worker')} ({d.get('model')}) attempt {d.get('attempt')}"
    elif e["kind"] == "claimed":
        summary = f"attempt {d.get('attempt')} · lease by {str(d.get('owner', ''))[-14:]}"
    elif e["kind"] == "lesson":
        summary = str(d.get("text", ""))[:90]
    elif e["kind"] == "added":
        summary = str(d.get("title", ""))[:70]
    elif e["kind"] == "planned":
        summary = f"{len(d.get('items', []))} items from the goal"
    else:
        summary = short(d, 90)
    journal_lines.append(f"{e['seq']:>4}  {rel(e['ts'])}  {str(e['item_id'] or '—'):<11} {e['kind']:<17} {summary}")

per_item = {}
for e in ev:
    if e["item_id"]:
        per_item.setdefault(e["item_id"], []).append(e["kind"])

run_log = read(S / "run.log")
run_excerpt = "\n".join(l for l in run_log.splitlines() if "⚙" not in l)[:6000]
git_log = sh("git log --oneline --reverse")
files = sh("ls -la *.md *.csv tests 2>/dev/null")
budget_csv = read(PROJ / "budget.csv")
budget_test = read(PROJ / "tests" / "test_budget.py")
flights_head = "\n".join(read(PROJ / "flights.md").splitlines()[:25])
mas_dir_during = read(S / "mas-dir-during-run.txt")
status_during = read(S / "status-during.txt")
status_after = sh(f"MAS_PLAIN=1 {Path(sys.executable).with_name('mas')} status")
wal_now = sh("ls -la .mas")
first_claim = min((e["ts"] for e in ev if e["kind"] == "claimed"), default=t0)
last_done = max((e["ts"] for e in ev if e["kind"] in ("done", "parked")), default=t0)
cost = sum((json.loads(e["data"]).get("cost_usd") or 0) for e in ev if e["kind"] == "worker_finished")
tokens = sum((json.loads(e["data"]).get("tokens") or 0) for e in ev if e["kind"] == "worker_finished")

doc = f"""# One goal, end to end: what `mas` does with "{GOAL}"

*A walkthrough built from a real run on {time.strftime('%Y-%m-%d')}. Every box below is copied from the tool's own
evidence: the prompt it sent, the JSON it got back, the rows in the SQLite board, the append-only event log,
the files that landed, and the git history. Nothing is illustrative; it all happened.*

Reproduce it in three commands:

```bash
mkdir ~/mas-trip && cd ~/mas-trip && git init -q -b main && echo "# Trip plan" > README.md && git add -A && git commit -qm init
mas init && mas plan "{GOAL}" --n 8
mas run --workers claude          # in a second terminal: mas watch
```

---

## Step 1 · The goal is one sentence

You do not write tasks. You state the goal:

```bash
mas plan "{GOAL}" --n 8
```

`mas plan` is the only place a model is allowed to shape the work. Everything after it is code.

## Step 2 · What the planner is actually asked

`mas` builds one prompt from a fixed template, your goal, and a listing of the (empty) project folder. This is
the exact text sent to Claude Code, in plan mode (read-only tools), with a JSON schema that forces the answer
into a list of items:

{fence(plan.get('prompt', '(prompt not captured)'))}

Notice what it asks for: independent, window-sized pieces; a brief a stranger can pick up cold; a **check** that a
program can run; the files each piece may write; and dependencies only when one piece needs another's file.

## Step 3 · What the planner answered

The model returned {len(raw_items)} items as JSON (schema-enforced, so there is nothing to parse by hand).
Three of them, verbatim:

{fence(json.dumps(raw_items[:1] + raw_items[-2:], indent=1, ensure_ascii=False)[:5000], 'json')}

Read the `check` fields: they are shell commands. `flights` must produce a file that mentions Tel Aviv, a
return leg, and a dollar amount. `budget` must pass a pytest file. `budget` also declares
`depends_on` on four other items, so it will not start until their files have landed.

`mas` validates this before anything touches the board: entries missing a title, brief or check are dropped,
ids are slugged and made unique, dependencies are resolved by id or title and unknown ones are removed.
It then writes the accepted items to the board and saves this whole exchange as `.mas/last_plan.json`.

## Step 4 · The board, before anything runs

The board is one SQLite file, `.mas/board.db`, in write-ahead-log mode:

{fence(tables_block)}

One row per task. `status=open`, no owner, no attempts. The `budget` row carries its dependencies and the
two files it is allowed to land:

{fence(items_block)}

The event log has already begun. Adding items and planning are the first entries, so the journal starts with
the decision, not with the work:

{fence(events_before)}

### The prompt a worker will receive

When the `flights` item is claimed, its worker gets exactly this. It is built from the row: a fixed frame, the
title, the brief, and the check it will be judged by. The worker sees nothing else — not the goal, not the
other items:

{fence(prompt_block)}

## Step 5 · `mas run`

`mas run --workers claude` starts the orchestrator: plain code, no model in the loop. It claims open items
(four at a time by default), gives each a fresh git worktree, runs the worker, re-runs the check itself, lands
the verified files on `main`, and writes every step to the log. The run log, with the per-tool-call lines removed:

{fence(run_excerpt)}

### The `.mas` directory while workers are running

Three database files and one compartment per attempt in `work/`:

{fence(mas_dir_during)}

`board.db` is the main file. `board.db-wal` is the write-ahead log: SQLite appends changed pages there
first, so readers (the live view, `mas watch`, another orchestrator) never block writers. `board.db-shm` is
the shared index over the WAL. On checkpoint the pages move into the main file. That is the whole
"distributed" state store: one file, copyable with `cp`, queryable with `sqlite3`.

The board mid-run — some items leased, `budget` still waiting on its dependencies:

{fence(status_during)}

## Step 6 · The complete journey, from the log

Every state change is one appended row in `events`. Time is relative to the first claim. Read one item
top to bottom and you have its life: claimed → compartment → dispatched → tool calls → worker finished →
gate → verified → merged → done → lesson.

{fence(chr(10).join(journal_lines)[:60000])}

Per item, the sequence of kinds:

{fence(chr(10).join(f"{k:<11} {' → '.join(v)}" for k, v in per_item.items()))}

Counts by kind: {', '.join(f'{k} {v}' for k, v in sorted(kinds.items(), key=lambda kv: -kv[1]))}.

## Step 6b · When the contract is wrong

The `budget` item failed three times and was parked. Not because the work was bad — because its check ran
`python -m pytest` and this machine has only `python3`. The planner copied the word `python` from the runner
hint it was given. The gate did exactly what it should: it refused to land work it could not verify, retried
with a stronger model, and after the third failure stopped and kept the evidence:

{fence(chr(10).join(l for l in journal_lines if ' budget ' in l and any(k in l for k in ('rejected', 'requeued', 'parked', 'dispatched', 'edited', 'unparked'))))}

Fixing it is a human decision and a human command — the contract is edited in place and the item is reopened.
Both are events in the same log, so the correction is part of the record:

```bash
mas show budget                                  # the evidence: three verdicts, "python: command not found"
mas edit budget --check "cmd:$(which python3) -m pytest -q tests/test_budget.py"
mas unpark budget
mas run --workers claude                         # only budget is open; its four dependencies are already done
```

{fence(read(S / "run2.log").replace(chr(10) + chr(10), chr(10))[:3000] if (S / "run2.log").exists() else "(second run not recorded)")}

Two lessons the environment cannot learn for you: make the runner in the planner prompt a concrete interpreter
(it now uses the exact Python that runs `mas`), and remember that a check is only as good as the command behind it.

## Step 7 · What came out

The board after the run:

{fence(status_after)}

One commit per verified item on `main` — the audit trail is the git history:

{fence(git_log)}

The files the workers landed:

{fence(files)}

The budget item was gated by a test written for it. This is the test and the data it checked:

{fence(budget_test[:2500], 'python')}
{fence(budget_csv[:2500], 'csv')}

The first lines of `flights.md`:

{fence(flights_head)}

Lessons left on the board by finished workers, shown to later workers as context:

{fence(chr(10).join(f"[{l['item_id']}] {l['text'][:160]}" for l in lessons) or '(none)')}

Totals: wall time {last_done - first_claim:.0f} s from first claim to last landing · tokens {tokens:,} · cost ${cost:.2f}.

## Step 8 · Reading the database yourself

```bash
sqlite3 ~/mas-trip/.mas/board.db "pragma journal_mode;"
sqlite3 ~/mas-trip/.mas/board.db "select id, status, attempts, depends_on from items;"
sqlite3 ~/mas-trip/.mas/board.db "select seq, item_id, kind, substr(data,1,80) from events order by seq;"
sqlite3 ~/mas-trip/.mas/board.db "select item_id, text from lessons;"
mas events -n 200          # the same, colored
mas show budget            # one item and its whole history
```

The `.mas` directory after the run (the `-wal` and `-shm` files disappear when the last connection closes and
SQLite checkpoints; while any process holds the database open they are there):

{fence(wal_now)}

## What to notice

- **The plan is evidence, not a conversation.** The prompt, the JSON, and the accepted rows are all on disk.
  You can diff what the model proposed against what the board accepted.
- **Dependencies are rows, not a scheduler's memory.** `budget` became claimable only when its four inputs
  were `done`; the claim query enforces it inside the database.
- **The gate is a shell command the worker was told about.** Workers claim success; the orchestrator re-runs
  the check in the worker's own compartment before anything lands.
- **The contract can be wrong.** The planner let `budget` write its own test. That test could be too lenient
  or simply wrong, and the environment cannot tell. For code we derive checks from fixtures; for a trip, a
  human reading `budget.csv` is the real gate.
- **A check is only as good as the command behind it.** `budget` was rejected three times by `python: command
  not found`, not by bad work. The breaker parked it with the evidence, a human edited the contract, and the
  same board resumed. The fix went into the tool too: the planner now names the exact interpreter.
- **Everything survives a crash.** Kill the run at any point; `mas run` again continues from the rows.
"""
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(doc)
print(f"wrote {OUT} ({len(doc):,} chars); events {len(ev)}; items {len(items)}; cost ${cost:.2f}")
