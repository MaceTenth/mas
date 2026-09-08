"""Unit tests for the mas environment — no LLM involved.

They pin the invariants the orchestrator relies on:
  * exactly one claimant wins an item; exhausted items are never handed out
  * heartbeats keep a lease; a dead owner's lease expires (or trips the breaker
    on the final attempt)
  * fail() backs off then parks; release() refunds the attempt
  * merges are idempotent; compartments are per attempt
  * concurrent landings serialize shared Git state; new output trees expand
  * the orchestrator loop, driven by a fake worker, gates work and resumes
"""
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mas.board import SQLiteBoard, Item, OPEN, LEASED, DONE, PARKED   # noqa: E402
from mas.workspace import Workspace                                    # noqa: E402
from mas.verify import run_check                                       # noqa: E402


@pytest.fixture(autouse=True)
def _clear_stop_flag():
    """The graceful-stop flag is process-wide; never let one test's stop leak into the next."""
    from mas.workers import STOP
    STOP.clear()
    yield
    STOP.clear()


# ------------------------------------------------------------------ board
@pytest.fixture
def board(tmp_path):
    return SQLiteBoard(tmp_path / "board.db")


def add(board, id, **kw):
    return board.add(Item(id=id, title=id, brief="do it", **kw))


def test_claim_is_exclusive_and_orders_by_priority(board):
    add(board, "low", priority=0)
    add(board, "high", priority=5)
    a = board.claim("w1", 60, ["claude"])
    b = board.claim("w2", 60, ["claude"])
    c = board.claim("w3", 60, ["claude"])
    assert (a.id, b.id, c) == ("high", "low", None)
    assert a.status == LEASED and a.attempts == 1 and a.lease_owner == "w1"


def test_claim_respects_worker_pref(board):
    add(board, "only-codex", worker_pref="codex")
    assert board.claim("w", 60, ["claude"]) is None
    assert board.claim("w", 60, ["claude", "codex"]).id == "only-codex"


def test_claim_never_hands_out_exhausted_items(board):
    add(board, "x", max_attempts=1)
    it = board.claim("w1", 0.01, ["claude"])
    assert it.attempts == 1
    time.sleep(0.02)
    expired = board.expire_leases()                # final attempt died → breaker, not requeue
    assert expired == ["x"]
    assert board.get("x").status == PARKED
    assert board.claim("w2", 60, ["claude"]) is None
    assert board.get("x").verdict["kind"] == "lease_expired"


def test_heartbeat_keeps_lease_and_expiry_reopens(board):
    add(board, "x")
    board.claim("w1", 0.05, ["claude"])
    assert board.heartbeat("x", "w1", 60) is True
    assert board.heartbeat("x", "someone-else", 60) is False
    assert board.expire_leases() == []             # renewed → still leased
    board.heartbeat("x", "w1", 0.01)
    time.sleep(0.02)
    assert board.expire_leases() == ["x"]
    x = board.get("x")
    assert x.status == OPEN and x.lease_owner is None and x.attempts == 1
    assert board.heartbeat("x", "w1", 60) is False  # the old owner has truly lost it


def test_fail_backs_off_then_parks_with_escalating_attempts(board):
    add(board, "x", max_attempts=2)
    board.claim("w1", 60, ["claude"])
    assert board.fail("x", "w1", {"passed": False}, backoff_base=0.05) == OPEN
    x = board.get("x")
    assert x.status == OPEN and x.next_eligible_at > time.time()
    assert board.claim("w2", 60, ["claude"]) is None     # in backoff
    time.sleep(0.1)
    it = board.claim("w2", 60, ["claude"])
    assert it.attempts == 2
    assert board.fail("x", "w2", {"passed": False}, backoff_base=0.05) == PARKED
    assert board.get("x").status == PARKED
    assert board.unpark("x") and board.get("x").attempts == 0


def test_complete_and_fail_require_ownership(board):
    add(board, "x")
    board.claim("w1", 60, ["claude"])
    assert board.complete("x", "impostor", {"passed": True}) is False
    assert board.fail("x", "impostor", {"passed": False}) == "lost"
    assert board.complete("x", "w1", {"passed": True}) is True
    assert board.get("x").status == DONE
    assert board.pending() == 0


def test_release_refunds_the_attempt(board):
    add(board, "x")
    board.claim("w1", 60, ["claude"])
    assert board.release("x", "w1") is True
    x = board.get("x")
    assert x.status == OPEN and x.attempts == 0 and x.lease_owner is None
    assert board.release("x", "w1") is False
    assert [e["kind"] for e in board.events("x")] == ["added", "claimed", "released"]


def test_events_and_lessons_are_append_only(board):
    add(board, "x")
    board.add_lesson("grep before you read", "x")
    board.add_lesson("run the check yourself", "x")
    assert [l["text"] for l in board.lessons(5)] == ["grep before you read", "run the check yourself"]
    kinds = [e["kind"] for e in board.events()]
    assert kinds == ["added", "lesson", "lesson"]
    assert board.stats()["by_status"] == {"open": 1}


# -------------------------------------------------------------- workspace
def git(*args, cwd):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "proj"
    root.mkdir()
    (root / "src").mkdir()
    (root / "src" / "a.py").write_text("x = 1\n")
    (root / "src" / "b.py").write_text("y = 1\n")
    git("init", "-q", cwd=root)
    git("-c", "user.email=t@t", "-c", "user.name=t", "add", ".", cwd=root)
    git("-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "init", cwd=root)
    return root


def test_compartments_are_per_attempt_and_isolated(repo):
    ws = Workspace(repo)
    p1 = ws.prepare("item-a1")
    p2 = ws.prepare("item-a2")
    assert p1 != p2 and p1.exists() and p2.exists()
    (p1 / "src" / "a.py").write_text("x = 2\n")
    assert (p2 / "src" / "a.py").read_text() == "x = 1\n"      # bulkhead
    assert (repo / "src" / "a.py").read_text() == "x = 1\n"    # main untouched
    ws.cleanup("item-a1", p1)
    assert not p1.exists() and p2.exists()                     # cleaning one never touches the other
    assert ".mas/" in (repo / ".gitignore").read_text()


def test_merge_is_idempotent_and_skips_noise(repo):
    ws = Workspace(repo)
    p = ws.prepare("k-a1")
    (p / "src" / "a.py").write_text("x = 2\n")
    (p / "src" / "__pycache__").mkdir()
    (p / "src" / "__pycache__" / "a.pyc").write_bytes(b"junk")
    (p / "notes").mkdir()
    (p / "notes" / "scratch.txt").write_text("hi")
    changed = ws.changed_files(p)
    assert "src/a.py" in changed and not any("__pycache__" in c for c in changed)
    assert ws.merge(p, ["src/a.py"]) == ["src/a.py"]
    assert ws.merge(p, ["src/a.py"]) == []                     # second landing is a no-op
    assert (repo / "src" / "a.py").read_text() == "x = 2\n"
    sha = ws.commit("mas: land a", ["src/a.py"])
    assert sha and len(sha) >= 7
    assert ws.commit("mas: nothing", []) is None


# ----------------------------------------------------------------- verify
def test_gate_runs_commands_and_never_trusts_the_worker(tmp_path):
    ok = run_check(Item(id="i", title="t", brief="b", check="cmd:exit 0"), tmp_path, 30)
    bad = run_check(Item(id="i", title="t", brief="b", check="cmd:echo boom >&2; exit 3"), tmp_path, 30)
    assert ok.passed and not bad.passed and "boom" in bad.detail
    assert run_check(Item(id="i", title="t", brief="b", check="human"), tmp_path, 30).kind == "human"
    assert run_check(Item(id="i", title="t", brief="b", check="none"), tmp_path, 30).passed


# ------------------------------------------------------------ orchestrator
class FakeWorker:
    """Writes the fix on demand — or nothing — so the gate, not the worker, decides."""
    calls = []

    def __init__(self, behaviour):
        self.behaviour = behaviour

    def run(self, prompt, cwd, model, max_turns, timeout_s, on_activity=None):
        from mas.workers import WorkerResult
        FakeWorker.calls.append((cwd.name, model))
        if on_activity:
            on_activity("Edit", "src/a.py")
        if self.behaviour == "fix":
            (Path(cwd) / "src" / "a.py").write_text("x = 42\n")
            return WorkerResult(True, summary="set x to 42")
        return WorkerResult(True, summary="I am sure I fixed it (I did not)")   # a liar


def make_orch(repo, board, behaviour, monkeypatch, **cfg):
    from mas import orchestrator as om
    monkeypatch.setattr(om, "make_worker", lambda kind, config, check_cmd=None, context=None: FakeWorker(behaviour))
    config = {"lease_seconds": 30, "heartbeat_seconds": 30, "max_turns": 3, "attempt_timeout_seconds": 30,
              "backoff_base_seconds": 0.01, "models": {"claude": ["haiku", "sonnet"]}, "share_lessons": True, **cfg}
    return om.Orchestrator(board, Workspace(repo), config, ["claude"], concurrency=2, log=lambda m: None)


def test_orchestrator_gates_merges_and_learns(repo, monkeypatch):
    FakeWorker.calls.clear()
    board = SQLiteBoard(repo / ".mas" / "board.db")
    check = f"cmd:{sys.executable} -c \"import sys; sys.exit(0 if open('src/a.py').read().strip()=='x = 42' else 1)\""
    board.add(Item(id="fix-a", title="make x 42", brief="", check=check, merge_paths=["src/a.py"]))
    orch = make_orch(repo, board, "fix", monkeypatch)
    stats = orch.run()
    assert stats["by_status"] == {"done": 1}
    assert (repo / "src" / "a.py").read_text() == "x = 42\n"
    log = subprocess.run(["git", "log", "--oneline"], cwd=repo, capture_output=True, text=True).stdout
    assert "mas: make x 42 [fix-a]" in log
    assert FakeWorker.calls == [("fix-a-a1", "haiku")]
    assert board.lessons(1)[0]["text"].startswith("[make x 42]")
    kinds = [e["kind"] for e in board.events("fix-a")]
    assert kinds == ["added", "claimed", "compartment", "dispatched", "activity", "worker_finished", "gate", "verified", "merged", "done", "lesson"]
    run_kinds = [e["kind"] for e in board.events() if e["item_id"] is None]
    assert run_kinds == ["run_started", "run_finished"]
    assert not (repo / ".mas" / "work" / "fix-a-a1").exists()     # compartment cleaned


def test_orchestrator_serializes_shared_git_landings(repo, monkeypatch):
    """Parallel workers are fine; shared root merge+commit must be one atomic boundary."""
    import shlex
    import threading
    from mas import orchestrator as om
    from mas.workers import WorkerResult

    class ParallelFixer:
        def run(self, prompt, cwd, model, max_turns, timeout_s, on_activity=None):
            rel = "src/a.py" if Path(cwd).name.startswith("fix-a-") else "src/b.py"
            (Path(cwd) / rel).write_text("value = 42\n")
            return WorkerResult(True, summary=f"fixed {rel}")

    board = SQLiteBoard(repo / ".mas" / "board.db")
    py = shlex.quote(sys.executable)
    for name in ("a", "b"):
        rel = f"src/{name}.py"
        check = f"cmd:{py} -c \"assert open('{rel}').read() == 'value = 42\\n'\""
        board.add(Item(id=f"fix-{name}", title=f"fix {name}", brief="", check=check, merge_paths=[rel]))
    monkeypatch.setattr(om, "make_worker", lambda *args, **kwargs: ParallelFixer())

    active = 0
    peak = 0
    guard = threading.Lock()
    original_commit = Workspace.commit

    def observed_commit(self, message, files):
        nonlocal active, peak
        with guard:
            active += 1
            peak = max(peak, active)
        time.sleep(0.05)
        try:
            return original_commit(self, message, files)
        finally:
            with guard:
                active -= 1

    monkeypatch.setattr(Workspace, "commit", observed_commit)
    cfg = {"lease_seconds": 30, "heartbeat_seconds": 1, "max_turns": 2, "attempt_timeout_seconds": 10,
           "backoff_base_seconds": 0.01, "models": {"claude": ["tiny"]}}
    stats = om.Orchestrator(board, Workspace(repo), cfg, ["claude"], concurrency=2, log=lambda _: None).run(poll_s=0.01)
    assert stats["by_status"] == {"done": 2} and peak == 1
    assert not any(e["kind"] == "orchestrator_error" for e in board.events())


def test_orchestrator_rejects_liars_escalates_and_parks(repo, monkeypatch):
    FakeWorker.calls.clear()
    board = SQLiteBoard(repo / ".mas" / "board.db")
    board.add(Item(id="fix-a", title="t", brief="", check="cmd:exit 1", merge_paths=["src/a.py"], max_attempts=2))
    orch = make_orch(repo, board, "lie", monkeypatch)
    stats = orch.run()
    assert stats["by_status"] == {"parked": 1}
    assert [m for _, m in FakeWorker.calls] == ["haiku", "sonnet"]          # escalation on retry
    assert (repo / "src" / "a.py").read_text() == "x = 1\n"                 # nothing unverified landed
    it = board.get("fix-a")
    assert it.attempts == 2 and it.meta.get("parked_workdir", "").endswith("fix-a-a2")
    kinds = [e["kind"] for e in board.events("fix-a")]
    assert kinds.count("rejected") == 2 and "parked" in kinds and "done" not in kinds


def test_orchestrator_resumes_after_a_crash(repo, monkeypatch):
    """Simulate a crash: an item is left leased by a dead owner; the next run takes it over."""
    FakeWorker.calls.clear()
    board = SQLiteBoard(repo / ".mas" / "board.db")
    check = f"cmd:{sys.executable} -c \"import sys; sys.exit(0 if open('src/a.py').read().strip()=='x = 42' else 1)\""
    board.add(Item(id="fix-a", title="t", brief="", check=check, merge_paths=["src/a.py"]))
    dead = board.claim("dead-orchestrator", 0.01, ["claude"])              # crashed mid-attempt 1
    assert dead.attempts == 1
    time.sleep(0.02)
    orch = make_orch(repo, board, "fix", monkeypatch)
    stats = orch.run()
    assert stats["by_status"] == {"done": 1}
    assert FakeWorker.calls == [("fix-a-a2", "sonnet")]                     # resumed as attempt 2, escalated
    kinds = [e["kind"] for e in board.events("fix-a")]
    assert "lease_expired" in kinds and kinds[-1] in ("done", "lesson")


def test_orchestrator_graceful_stop_releases_leases(repo, monkeypatch):
    """stop() mid-run: no gate, no merge, lease handed back, attempt refunded."""
    board = SQLiteBoard(repo / ".mas" / "board.db")
    board.add(Item(id="slow", title="t", brief="", check="cmd:exit 0", merge_paths=["src/a.py"]))
    board.add(Item(id="slow2", title="t", brief="", check="cmd:exit 0", merge_paths=["src/b.py"]))
    from mas import orchestrator as om
    import threading

    class SlowWorker:
        def run(self, prompt, cwd, model, max_turns, timeout_s, on_activity=None):
            from mas.workers import WorkerResult, STOP
            STOP.wait(10)
            return WorkerResult(False, error="interrupted")
    monkeypatch.setattr(om, "make_worker", lambda kind, config, check_cmd=None, context=None: SlowWorker())
    config = {"lease_seconds": 30, "heartbeat_seconds": 30, "max_turns": 3, "attempt_timeout_seconds": 30,
              "backoff_base_seconds": 0.01, "models": {"claude": ["haiku"]}}
    orch = om.Orchestrator(board, Workspace(repo), config, ["claude"], concurrency=2, log=lambda m: None)
    t = threading.Thread(target=lambda: orch.run(poll_s=0.05)); t.start()
    deadline = time.time() + 5
    def st(i):
        it = board.get(i)
        if it is None:
            raise AssertionError(f"item {i!r} vanished; board has {[x.id for x in board.list()]}; db={board.path} exists={board.path.exists()}")
        return it.status
    while any(st(i) != LEASED for i in ("slow", "slow2")) and time.time() < deadline:
        time.sleep(0.02)
    assert all(st(i) == LEASED for i in ("slow", "slow2"))
    orch.stop(); t.join(10)
    assert not t.is_alive() and orch.interrupted
    assert orch._released == {"slow", "slow2"}
    for i in ("slow", "slow2"):
        it = board.get(i)
        assert it.status == OPEN and it.attempts == 0 and it.lease_owner is None
        kinds = [e["kind"] for e in board.events(i)]
        assert kinds.count("released") == 1 and "done" not in kinds and "rejected" not in kinds
    assert board.pending() == 2 and not (repo / ".mas" / "work").exists() or not any((repo / ".mas" / "work").iterdir())
    from mas.workers import STOP
    STOP.clear()


# -------------------------------------------------------------------- views
def test_every_event_kind_renders_and_the_live_view_never_crashes(repo, monkeypatch):
    """The view is a read model over the log: it must render every kind, even with empty data."""
    from rich.console import Console
    from mas import ui
    board = SQLiteBoard(repo / ".mas" / "board.db")
    board.add(Item(id="i1", title="t", brief="", check="cmd:exit 0"))
    board.add(Item(id="i2", title="t", brief="", check="cmd:exit 1", max_attempts=1))
    board.claim("w", 60, ["claude"])                       # i1 leased
    for kind in list(ui.KINDS) + ["some_future_kind"]:
        board.log("i1", kind, {})                          # empty payloads must not crash the formatter
    board.log(None, "run_started", {"workers": ["claude"], "models": {"claude": ["haiku"]}})
    for ev in board.events(limit=100):
        assert ui.format_event(ev).plain
    con = Console(record=True, width=120, height=40, force_terminal=True)
    view = ui.LiveUI(board, cfg={"workers": ["claude"]}, console_=con, title="test")
    con.print(view._render())
    out = con.export_text()
    assert "mas" in out and "i1" in out and "event log" in out and "working" in out
    # one-shot views
    ui.console = Console(record=True, width=120, force_terminal=True)
    ui.print_status(board); ui.print_events(board, 10); ui.print_summary(board, time.time() - 5)
    assert "i2" in ui.console.export_text()


# -------------------------------------------------------------------- demos
def test_demo_registry_bakes_flags_into_config_and_assigns_workers(tmp_path):
    import json
    from mas.demo import init_demo, DEMOS
    dest, items = init_demo(tmp_path / "d2", demo="2", base_config={"max_attempts": 3, "models": {"claude": ["haiku"]}})
    cfg = json.loads((dest / ".mas" / "config.json").read_text())
    assert cfg["workers"] == ["claude", "codex"] and cfg["lease_seconds"] == DEMOS["2"]["config"]["lease_seconds"] and cfg["demo"] == "2"
    assert cfg["models"] == {"claude": ["haiku"]}                      # base config survives
    assert [i.worker_pref for i in items] == ["claude", "codex"] * 4    # 4 / 4 split
    board = SQLiteBoard(dest / ".mas" / "board.db")
    assert board.claim("w", 60, ["codex"]).worker_pref == "codex"      # a codex-only fleet only sees its items
    # refusal rules
    with pytest.raises(SystemExit):
        init_demo(dest, demo="1")                                       # not empty, no --force
    (tmp_path / "plain").mkdir(); (tmp_path / "plain" / "keep").write_text("x")
    with pytest.raises(SystemExit):
        init_demo(tmp_path / "plain", demo="1", force=True)             # never wipes a non-mas directory
    assert (tmp_path / "plain" / "keep").exists()
    dest1, items1 = init_demo(dest, demo="1", force=True)               # reset works
    assert all(i.worker_pref is None for i in items1)
    assert json.loads((dest1 / ".mas" / "config.json").read_text())["workers"] == ["claude"]


def test_demo_run_force_explicitly_replaces_non_mas_directory(tmp_path, monkeypatch, capsys):
    from mas import cli

    occupied = tmp_path / "old-output"
    occupied.mkdir()
    (occupied / "important.txt").write_text("old\n")
    monkeypatch.setattr(cli, "shutil_which", lambda _: "/fake/worker")
    monkeypatch.setattr(cli, "cmd_run", lambda *args, **kwargs: None)

    with pytest.raises(SystemExit) as exc:
        cli.main(["demo", "run", "1", "--dir", str(occupied), "--plain"])
    assert "--force" in str(exc.value) and (occupied / "important.txt").exists()

    cli.main(["demo", "run", "1", "--dir", str(occupied), "--force", "--plain"])
    assert not (occupied / "important.txt").exists()
    assert (occupied / ".mas" / "board.db").exists()
    assert "removed existing demo directory (--force)" in capsys.readouterr().out


# ----------------------------------------------------------------- harnesses
def test_any_headless_cli_is_a_worker_via_config(repo, tmp_path):
    """Pluggability: a harness is described in config, not in code. Here the 'harness' is a shell script."""
    from mas import orchestrator as om
    script = tmp_path / "fakebot.sh"
    script.write_text("#!/bin/sh\n# args: --task <prompt-file> --model <model>\necho \"fakebot starting ($4)\"\n"
                      "grep -q 'TASK:' \"$2\" || exit 9\nprintf 'x = 42\\n' > src/a.py\necho 'fakebot: wrote src/a.py'\n")
    script.chmod(0o755)
    board = SQLiteBoard(repo / ".mas" / "board.db")
    check = f"cmd:{sys.executable} -c \"import sys; sys.exit(0 if open('src/a.py').read().strip()=='x = 42' else 1)\""
    board.add(Item(id="fix-a", title="make x 42", brief="", check=check, merge_paths=["src/a.py"], worker_pref="fakebot"))
    config = {"lease_seconds": 30, "heartbeat_seconds": 30, "max_turns": 3, "attempt_timeout_seconds": 30, "backoff_base_seconds": 0.01,
              "models": {"fakebot": ["tiny", "big"]},
              "harnesses": {"fakebot": {"cmd": [str(script), "--task", "{prompt_file}", "--model", "{model}"],
                                        "prompt_via": "file", "summary": "stdout_tail", "activity": "lines"}}}
    orch = om.Orchestrator(board, Workspace(repo), config, ["claude", "fakebot"], concurrency=1, log=lambda m: None)
    stats = orch.run()
    assert stats["by_status"] == {"done": 1}
    assert (repo / "src" / "a.py").read_text() == "x = 42\n"
    evs = board.events("fix-a")
    disp = [e for e in evs if e["kind"] == "dispatched"][0]["data"]
    assert disp["worker"] == "fakebot" and disp["model"] == "tiny"           # worker_pref + model tiers work for any kind
    acts = [e["data"]["arg"] for e in evs if e["kind"] == "activity"]
    assert any("fakebot starting (tiny)" in a for a in acts)                 # its stdout became live activity
    fin = [e for e in evs if e["kind"] == "worker_finished"][0]["data"]
    assert fin["ok"] and "wrote src/a.py" in fin["summary"]
    # a missing binary is a clean failure, not a crash
    from mas.workers import ExecWorker
    r = ExecWorker("ghost", {"cmd": ["/nonexistent/ghost", "{prompt}"]}).run("p", repo, None, 1, 5)
    assert not r.ok and "not found" in r.error


# ------------------------------------------------------------ dependencies
def test_depends_on_blocks_claims_until_dependencies_are_done(board):
    add(board, "a")
    add(board, "b", depends_on=["a"], priority=99)      # higher priority, but blocked
    add(board, "c", depends_on=["a", "b"])
    assert board.claim("w", 60, ["claude"]).id == "a"    # b and c wait
    assert board.claim("w", 60, ["claude"]) is None
    board.complete("a", "w", {"passed": True})
    assert board.claim("w", 60, ["claude"]).id == "b"
    assert board.claim("w", 60, ["claude"]) is None      # c still waits for b
    board.complete("b", "w", {"passed": True})
    assert board.claim("w", 60, ["claude"]).id == "c"
    assert board.get("c").depends_on == ["a", "b"]       # round-trips through the row


def test_demo_3_wires_votes_debate_and_tally(tmp_path):
    import json
    from mas.demo import init_demo
    dest, items = init_demo(tmp_path / "d3", demo="3", base_config={"max_attempts": 3})
    ids = [i.id for i in items]
    assert ids[:8] == [f"vote-{i}-{'claude' if i % 2 else 'codex'}" for i in range(1, 9)] and ids[8:] == ["debate", "tally"]
    debate, tally = items[8], items[9]
    assert debate.depends_on == ids[:8] and debate.meta["model"] == "sonnet" and debate.check == "schema:final.json"
    assert tally.depends_on == ids[:8] + ["debate"] and tally.worker_pref == "tally"
    cfg = json.loads((dest / ".mas" / "config.json").read_text())
    assert cfg["workers"] == ["claude", "codex", "tally"] and cfg["harnesses"]["tally"]["cmd"][1].endswith("tally.py")
    assert (dest / "svc" / "profile_cache.py").exists() and (dest / "PR.md").exists() and not (dest / "tests").exists()
    board = SQLiteBoard(dest / ".mas" / "board.db")
    assert board.claim("w", 60, ["tally"]) is None                    # nothing for the tally until votes + debate land
    assert board.claim("w", 60, ["codex"]).id == "vote-2-codex"
    # the tally script itself, on synthetic votes
    import subprocess, sys as _sys
    (dest / "votes").mkdir()
    for i in range(1, 9):
        kind = "claude" if i % 2 else "codex"
        loc = "get_profile: cache key ignores include_private" if i != 4 else "unbounded cache growth"
        (dest / "votes" / f"vote-{i}-{kind}.json").write_text(json.dumps({"bug": True, "severity": "high", "location": loc, "scenario": "…", "fix": "…", "confidence": 0.9}))
    (dest / "final.json").write_text(json.dumps({"bug": True, "severity": "high", "location": "key = user_id drops include_private", "scenario": "…", "fix": "…", "agreed_with": ["vote-1-claude"], "overruled": ["vote-4-codex"], "reasoning": "…"}))
    r = subprocess.run([_sys.executable, cfg["harnesses"]["tally"]["cmd"][1], str(dest)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    tj = json.loads((dest / "result" / "tally.json").read_text())
    assert tj["majority"] == {"bug_yes": 8, "n": 8, "located_the_bug": 7, "correct": True}
    assert tj["by_harness"]["codex"]["found"] == 3 and tj["debate"]["correct"] is True
    assert "| majority vote of 8 | ✓ |" in (dest / "result" / "summary.md").read_text()


def test_settled_policy_lets_parked_dependencies_count(board):
    add(board, "v1", max_attempts=1)
    add(board, "v2")
    add(board, "strict", depends_on=["v1", "v2"])
    add(board, "tally", depends_on=["v1", "v2"], meta={"deps": "settled"})
    board.claim("w", 60, ["claude"]); board.fail("v1", "w", {"passed": False})         # v1 parks (max_attempts=1)
    assert board.get("v1").status == PARKED
    board.claim("w", 60, ["claude"]); board.complete("v2", "w", {"passed": True})
    assert board.claim("w", 60, ["claude"]).id == "tally"                               # settled: parked counts
    assert board.claim("w", 60, ["claude"]) is None                                     # strict still waits for v1


def test_demo_4_many_eyes_wiring_and_tally(tmp_path):
    import json, subprocess, sys as _sys
    from mas.demo import init_demo
    dest, items = init_demo(tmp_path / "d4", demo="4", base_config={"max_attempts": 3})
    ids = [i.id for i in items]
    assert ids[:8] == [f"vote-{i}-{'claude' if i % 2 else 'codex'}" for i in range(1, 9)] and ids[8:] == ["debate", "tally"]
    assert items[8].meta["deps"] == "settled" and items[8].meta["model"] == "sonnet"
    for f in ("svc/webhooks.py", "svc/api.py", "svc/billing.py", "svc/provider.py", "PR.md"):
        assert (dest / f).exists()
    cfg = json.loads((dest / ".mas" / "config.json").read_text())
    assert cfg["max_turns"] == 30 and cfg["harnesses"]["tally"]["cmd"][1].endswith("demo_review/tally.py")
    # single-kind fleet alternates models and says so in the id
    dest1, items1 = init_demo(tmp_path / "d4c", demo="4", base_config={}, fleet=["claude"])
    assert [i.id for i in items1[:2]] == ["vote-1-claude-haiku", "vote-2-claude-sonnet"] and items1[1].meta["model"] == "sonnet"
    assert json.loads((dest1 / ".mas" / "config.json").read_text())["workers"] == ["claude", "tally"]
    # tally on synthetic reviews: partial overlap → union beats every individual
    (dest / "votes").mkdir()
    F = lambda t, loc, sc: {"title": t, "location": loc, "severity": "high", "scenario": sc, "fix": "…"}
    b1 = F("webhook replay double credits", "svc/webhooks.py handle_webhook", "provider redelivers the same event id, balance credited twice")
    b2 = F("export lacks authorization", "svc/api.py export_invoices", "any user exports another account's invoices")
    b3 = F("cents truncated", "svc/billing.py line_total_cents", "int(19.99*3*100) gives 5996 not 5997")
    b4 = F("renew ignores failed charge", "svc/billing.py renew / provider.charge", "charge returns None yet status set active")
    fp = F("timing attack in signature", "svc/webhooks.py verify_signature", "attacker measures comparison time")
    reviews = {1: [b1, b2], 2: [b2, b3, fp], 3: [b1, b4], 4: [b3], 5: [b1, b2, b3], 6: [b4, fp], 7: [b2], 8: [b1, b3]}
    for i, fs in reviews.items():
        kind = "claude" if i % 2 else "codex"
        (dest / "votes" / f"vote-{i}-{kind}.json").write_text(json.dumps({"findings": fs, "confidence": 0.8}))
    (dest / "final.json").write_text(json.dumps({"findings": [b1, b2, b3, b4], "dropped": [{"title": fp["title"], "why": "compare_digest is constant-time"}], "reasoning": "…"}))
    r = subprocess.run([_sys.executable, cfg["harnesses"]["tally"]["cmd"][1], str(dest)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    tj = json.loads((dest / "result" / "tally.json").read_text())
    assert tj["union"]["recall"] == 1.0 and tj["debate"]["recall"] == 1.0 and tj["debate"]["unmatched"] == []
    assert tj["single"]["best"] == 0.75 and tj["single"]["worst"] == 0.25
    assert {b["id"]: b["found_by"] for b in tj["bugs"]} == {"B1": 4, "B2": 4, "B3": 4, "B4": 2}
    assert tj["majority"]["found"] == []                       # 4/8 is not more than half → majority misses everything here
    assert any("timing attack" in u for r_ in tj["reviewers"] for u in r_["unmatched"])
    assert "| union of 8 (found by anyone) | 100% |" in (dest / "result" / "summary.md").read_text()


# -------------------------------------------------------------------- cli: define a task from the command line
def test_cli_add_and_fanout_express_the_vote_pattern(repo, monkeypatch, tmp_path, capsys):
    import json
    from mas import cli
    monkeypatch.chdir(repo)
    cli.main(["init"])
    (tmp_path / "shape.json").write_text(json.dumps({"required": ["findings"], "properties": {"findings": {"type": "array"}}}))
    (tmp_path / "brief.md").write_text("Review PR as {persona}. Write votes/{id}.json  {\"findings\": []}")   # braces must survive
    cli.main(["fanout", "4", "Review PR as {persona}", "--fleet", "claude,codex", "--persona", "a maintainer", "--persona", "an auditor",
              "--brief-file", str(tmp_path / "brief.md"), "--check", "schema:votes/{id}.json", "--merge", "votes/{id}.json",
              "--schema", str(tmp_path / "shape.json"), "--slug", "review"])
    cli.main(["add", "Consolidate", "--brief", "read votes/*.json", "--check", "schema:final.json", "--merge", "final.json",
              "--worker", "claude", "--model", "sonnet", "--depends-on", "review-*", "--deps", "settled"])
    out = capsys.readouterr().out
    assert "added 4 items: review-1-claude, review-2-codex, review-3-claude, review-4-codex" in out
    board = SQLiteBoard(repo / ".mas" / "board.db")
    r1, r2, r3 = board.get("review-1-claude"), board.get("review-2-codex"), board.get("review-3-claude")
    assert r1.worker_pref == "claude" and r2.worker_pref == "codex"
    assert r1.title == "Review PR as a maintainer" and r3.title == "Review PR as an auditor"      # personas rotate per fleet round
    assert r1.check == "schema:votes/review-1-claude.json" and r1.merge_paths == ["votes/review-1-claude.json"]
    assert 'votes/review-1-claude.json  {"findings": []}' in r1.brief and r1.meta["schema"]["required"] == ["findings"]
    c = [i for i in board.list() if i.title == "Consolidate"][0]
    assert c.depends_on == ["review-1-claude", "review-2-codex", "review-3-claude", "review-4-codex"]
    assert c.meta == {"model": "sonnet", "deps": "settled"}
    assert board.claim("w", 60, ["claude"]).id == "review-1-claude"                               # consolidate waits
    with pytest.raises(SystemExit):
        cli.main(["add", "x", "--brief", "b", "--worker", "pi"])                                    # unknown worker is refused
    with pytest.raises(SystemExit):
        cli.main(["add", "x", "--brief", "b", "--depends-on", "nothing-*"])                        # dangling glob is refused


# ------------------------------------------------------------ spawn · run_last · exec context · github mirror · demo 5
def test_run_last_waits_for_everything_else(board):
    add(board, "a"); add(board, "b")
    add(board, "score", meta={"run_last": True})
    assert {board.claim("w", 60, ["claude"]).id, board.claim("w", 60, ["claude"]).id} == {"a", "b"}
    assert board.claim("w", 60, ["claude"]) is None                                   # b still leased
    board.complete("a", "w", {"passed": True}); board.fail("b", "w", {"passed": False}, backoff_base=0.01)
    assert board.claim("w", 60, ["claude"]) is None                                   # b is open again (backoff) → still waits
    time.sleep(0.05); board.claim("w", 60, ["claude"]); board.complete("b", "w", {"passed": True})
    assert board.claim("w", 60, ["claude"]).id == "score"


def test_planner_item_spawns_children_then_reviewer(repo, monkeypatch):
    """A finished item's PLAN.json becomes items; an `after` template depends on the whole batch."""
    import json
    from mas import orchestrator as om
    board = SQLiteBoard(repo / ".mas" / "board.db")

    class Planner:
        def run(self, prompt, cwd, model, max_turns, timeout_s, on_activity=None):
            from mas.workers import WorkerResult
            if (Path(cwd) / "PLAN.json").exists() or "plan" not in prompt.lower():
                return WorkerResult(True, summary="did the work")
            (Path(cwd) / "PLAN.json").write_text(json.dumps({"items": [
                {"id": "money", "title": "Implement money", "brief": "do money", "check": "cmd:exit 0", "merge_paths": ["ledger/money.py"]},
                {"id": "cli", "title": "Implement cli", "brief": "do cli", "check": "cmd:exit 0", "depends_on": ["money"], "model": "sonnet"},
                {"title": "broken entry without a check", "brief": "x"},
            ]}))
            return WorkerResult(True, summary="planned")
    monkeypatch.setattr(om, "make_worker", lambda kind, config, check_cmd=None, context=None: Planner())
    board.add(Item(id="plan", title="Plan", brief="plan the work", check="cmd:test -s PLAN.json", merge_paths=[],
                   meta={"spawn": {"file": "PLAN.json", "prefix": "do-",
                                   "defaults": {"worker": "claude", "model": "haiku", "brief_suffix": " RULES"},
                                   "after": [{"id": "review-1", "title": "Review", "brief": "review", "check": "cmd:exit 0", "worker": "claude",
                                              "meta": {"model": "sonnet", "deps": "settled"}}]}}))
    board.add(Item(id="score", title="Score", brief="s", check="cmd:exit 0", meta={"run_last": True}))
    config = {"lease_seconds": 30, "heartbeat_seconds": 30, "max_turns": 3, "attempt_timeout_seconds": 30, "backoff_base_seconds": 0.01,
              "models": {"claude": ["haiku"]}}
    orch = om.Orchestrator(board, Workspace(repo), config, ["claude"], concurrency=2, log=lambda m: None)
    stats = orch.run()
    ids = {i.id: i for i in board.list()}
    assert set(ids) == {"plan", "do-money", "do-cli", "review-1", "score"}                     # the broken entry was skipped
    assert ids["do-money"].worker_pref == "claude" and ids["do-money"].meta["model"] == "haiku" and ids["do-money"].brief.endswith("RULES")
    assert ids["do-cli"].depends_on == ["do-money"] and ids["do-cli"].meta["model"] == "sonnet"   # batch ids resolved, per-item model wins
    assert ids["review-1"].depends_on == ["do-cli", "do-money"] and ids["review-1"].meta["deps"] == "settled"
    assert stats["by_status"] == {"done": 5}
    order = [e["item_id"] for e in board.events() if e["kind"] == "done"]
    assert order.index("plan") < order.index("do-money") < order.index("do-cli") < order.index("review-1") < order.index("score")
    kinds = [e["kind"] for e in board.events("plan")]
    assert "spawned" in kinds and kinds.index("spawned") < kinds.index("done")                    # children exist before the parent is done


def test_exec_worker_context_placeholders(tmp_path):
    from mas.workers import ExecWorker
    w = ExecWorker("probe", {"cmd": ["/bin/sh", "-c", "echo board={board} root={root} cwd={cwd}"]}, context={"board": "/x/board.db", "root": "/x"})
    r = w.run("p", tmp_path, None, 1, 10)
    assert r.ok and "board=/x/board.db" in r.summary and "root=/x" in r.summary and f"cwd={tmp_path}" in r.summary


def test_github_mirror_creates_comments_and_closes(monkeypatch, board):
    from mas import github as gh
    calls = []
    def fake_gh(*args):
        calls.append(args)
        return "https://github.com/o/r/issues/42\n" if args[:2] == ("issue", "create") else ""
    monkeypatch.setattr(gh, "_gh", fake_gh)
    m = gh.GitHubMirror("o/r", labels=["mas", "demo5-team"])
    it = add(board, "plan", check="cmd:pytest -q", depends_on=[], meta={"model": "sonnet"})
    assert m.ensure_issue(it, board) == 42 and board.get("plan").meta["gh_number"] == 42 and it.meta["gh_repo"] == "o/r"
    assert m.ensure_issue(it, board) == 42 and sum(1 for c in calls if c[:2] == ("issue", "create")) == 1     # idempotent
    m.on_dispatched(it, "claude", "sonnet"); m.on_verdict(it, {"passed": True, "detail": "3 passed", "attempt": 1}, "summary here")
    m.on_spawned(it, [add(board, "do-money", meta={"gh_repo": "o/r", "gh_number": 43})]); m.on_done(it, {"worker": "claude", "attempt": 1, "commit": "abc"}, ["PLAN.json"])
    kinds = [c[:2] for c in calls]
    assert kinds.count(("issue", "comment")) == 3 and ("issue", "close") in kinds
    create = [c for c in calls if c[:2] == ("issue", "create")][0]
    assert "-l" in create and "demo5-team" in create and "check: `cmd:pytest -q`" in create[create.index("-b") + 1]
    assert any("#43" in c[-1] for c in calls if c[:2] == ("issue", "comment"))




def test_pinned_model_applies_to_first_attempt_then_escalates(repo, monkeypatch):
    FakeWorker.calls.clear()
    board = SQLiteBoard(repo / ".mas" / "board.db")
    board.add(Item(id="x", title="t", brief="", check="cmd:exit 1", merge_paths=["src/a.py"], max_attempts=3, meta={"model": "haiku"}))
    board.add(Item(id="y", title="t", brief="", check="cmd:exit 1", merge_paths=["src/a.py"], max_attempts=2, meta={"model": "opus"}))
    orch = make_orch(repo, board, "lie", monkeypatch, models={"claude": ["haiku", "sonnet"]})
    orch.run()
    by_item = {}
    for cwd, m in FakeWorker.calls:
        by_item.setdefault(cwd.split("-a")[0], []).append(m)
    assert by_item["x"] == ["haiku", "sonnet", "sonnet"]      # pinned first, then up the tiers
    assert by_item["y"] == ["opus", "opus"]                    # a pin outside the tiers stays pinned


def test_spawned_items_carry_their_issue_number_before_they_are_claimable(repo, monkeypatch):
    """Regression: a worker claimed a spawned item before its gh_number was written → no comments, never closed."""
    import json
    from mas import orchestrator as om, github as gh
    seen = {}
    class Mirror(gh.GitHubMirror):
        def __init__(self): super().__init__("o/r")
        def ensure_issue(self, item, board):
            item.meta.update(gh_repo="o/r", gh_number=100 + len(seen)); seen[item.id] = item.meta["gh_number"]
            if board.get(item.id): board.set_meta(item.id, **{k: item.meta[k] for k in ("gh_repo", "gh_number")})
            return item.meta["gh_number"]
        def on_dispatched(self, item, kind, model): seen.setdefault("dispatched", []).append((item.id, self._num(item)))
        def on_done(self, item, verdict, landed): seen.setdefault("done", []).append((item.id, self._num(item)))
        def on_spawned(self, item, batch): pass
        def on_verdict(self, item, vd, summary=""): pass
    class Planner:
        def run(self, prompt, cwd, model, max_turns, timeout_s, on_activity=None):
            from mas.workers import WorkerResult
            if "plan" in prompt.lower() and not (Path(cwd) / "PLAN.json").exists():
                (Path(cwd) / "PLAN.json").write_text(json.dumps({"items": [{"id": "a", "title": "A", "brief": "a", "check": "cmd:exit 0"}]}))
            return WorkerResult(True, summary="ok")
    monkeypatch.setattr(om, "make_worker", lambda kind, config, check_cmd=None, context=None: Planner())
    board = SQLiteBoard(repo / ".mas" / "board.db")
    board.add(Item(id="plan", title="Plan", brief="plan", check="cmd:test -s PLAN.json", meta={"spawn": {"file": "PLAN.json", "prefix": "do-"}}))
    config = {"lease_seconds": 30, "heartbeat_seconds": 30, "max_turns": 3, "attempt_timeout_seconds": 30, "backoff_base_seconds": 0.01, "models": {"claude": ["haiku"]}}
    om.Orchestrator(board, Workspace(repo), config, ["claude"], concurrency=2, github=Mirror(), log=lambda m: None).run()
    assert board.get("do-a").meta["gh_number"] == seen["do-a"]
    assert ("do-a", seen["do-a"]) in seen["dispatched"] and ("do-a", seen["do-a"]) in seen["done"]   # the claimed copy knew its issue


# ------------------------------------------------------------------ gemini worker (SDK call stubbed)
def test_gemini_worker_tool_loop(tmp_path, monkeypatch):
    from types import SimpleNamespace as NS
    from google.genai import types
    from mas.workers import GeminiApiWorker
    (tmp_path / "src").mkdir(); (tmp_path / "src" / "a.py").write_text("x = 1\n")
    script = [
        [types.Part.from_text(text="Let me look."), types.Part.from_function_call(name="read_file", args={"path": "src/a.py"})],
        [types.Part.from_function_call(name="edit_file", args={"path": "src/a.py", "old_string": "x = 1", "new_string": "x = 42"})],
        [types.Part.from_function_call(name="done", args={"summary": "set x to 42"})],
    ]
    seen = []
    def fake_generate(self, client, model, contents, config):
        seen.append((model, len(contents)))
        parts = script[len(seen) - 1]
        return NS(usage_metadata=NS(prompt_token_count=100, candidates_token_count=10, thoughts_token_count=0),
                  candidates=[NS(content=types.Content(role="model", parts=parts))])
    monkeypatch.setattr(GeminiApiWorker, "_client", lambda self: None)
    monkeypatch.setattr(GeminiApiWorker, "_generate", fake_generate)
    acts = []
    r = GeminiApiWorker(check_cmd="true").run("fix it", tmp_path, "gemini-2.5-flash", 10, 60, on_activity=lambda t, a: acts.append(t))
    assert r.ok and r.summary == "set x to 42" and r.turns == 3 and r.tokens == 330 and r.cost_usd == round(300 / 1e6 * 0.30 + 30 / 1e6 * 2.5, 4)
    assert (tmp_path / "src" / "a.py").read_text() == "x = 42\n"
    assert acts == ["💬", "read_file", "edit_file", "done"]
    assert [n for _, n in seen] == [1, 3, 5]                       # the transcript grows by model turn + tool results
    assert GeminiApiWorker(check_cmd=None).PRICES.get("gemini-9-ultra") is None   # unknown model → cost None, tokens still reported


def test_openai_worker_can_consult_read_only_adviser_and_accounts_by_role(tmp_path, monkeypatch):
    import json
    from types import SimpleNamespace as NS
    from mas.workers import OpenAIWorker

    (tmp_path / "src").mkdir(); (tmp_path / "src" / "policylog.py").write_text("def authorize(): pass\n")
    (tmp_path / "SPEC.md").write_text("Use the private conflict profile.\n")
    seen = []

    def response(rid, output, input_tokens, output_tokens, text=""):
        return NS(id=rid, output=output, output_text=text,
                  usage=NS(input_tokens=input_tokens, output_tokens=output_tokens,
                           input_tokens_details=NS(cached_tokens=10 if "exec" in rid else 0)))

    def call(name, arguments, cid):
        return NS(type="function_call", name=name, arguments=json.dumps(arguments), call_id=cid)

    def fake_create(self, client, **kwargs):
        seen.append(kwargs)
        if kwargs["model"].startswith("gpt-5.5"):
            assert "private conflict profile" in kwargs["input"] and "CERULEAN SECRET" in kwargs["input"]
            assert "tools" not in kwargs
            return response("advice-1", [], 500, 100, "Use the exact private precedence tuple.")
        executor_n = sum(1 for x in seen if x["model"].startswith("gpt-5.4-mini"))
        if executor_n == 1:
            names = [t["name"] for t in kwargs["tools"]]
            assert "ask_advisor" in names
            assert "MANDATORY CONSULTATION CHECKPOINT" in kwargs["instructions"]
            return response("exec-1", [call("ask_advisor", {"question": "What is the private profile?", "paths": ["SPEC.md", "src/policylog.py"]}, "c1")], 100, 20)
        assert "private precedence tuple" in kwargs["input"][0]["output"]
        assert kwargs["previous_response_id"] == "exec-1"
        return response("exec-2", [call("done", {"summary": "implemented the advised design"}, "c2")], 100, 20)

    monkeypatch.setattr(OpenAIWorker, "_client", lambda self: None)
    monkeypatch.setattr(OpenAIWorker, "_create", fake_create)
    activities = []
    worker = OpenAIWorker(check_cmd="true", advisor_model="gpt-5.5-2026-04-23", max_advice_calls=2,
                          min_advice_calls=1, advisor_context="CERULEAN SECRET")
    result = worker.run("fix it", tmp_path, "gpt-5.4-mini-2026-03-17", 6, 60,
                        on_activity=lambda tool, arg: activities.append((tool, arg)))
    assert result.ok and result.summary == "implemented the advised design" and result.turns == 2
    assert result.tokens == 840 and result.breakdown["advisor"]["calls"] == 1
    assert result.breakdown["advisor"]["successful_calls"] == 1
    assert result.breakdown["advisor"]["checkpoint_satisfied"] is True
    assert result.breakdown["executor"]["input"] == 200 and result.breakdown["advisor"]["output"] == 100
    assert result.cost_usd == 0.0058
    assert [a[0] for a in activities] == ["ask_advisor", "advisor", "done"]


def test_openai_worker_receives_direct_context_without_adviser_tool(tmp_path, monkeypatch):
    import json
    from types import SimpleNamespace as NS
    from mas.workers import OpenAIWorker

    seen = []

    def fake_create(self, client, **kwargs):
        seen.append(kwargs)
        assert kwargs["model"].startswith("gpt-5.4-mini")
        assert "PRIVATE ORGANIZATIONAL CONTEXT" in kwargs["input"]
        assert "CERULEAN SECRET" in kwargs["input"]
        assert "ask_advisor" not in [tool["name"] for tool in kwargs["tools"]]
        call = NS(type="function_call", name="done", arguments=json.dumps({"summary": "used direct context"}), call_id="c1")
        usage = NS(input_tokens=100, output_tokens=20, input_tokens_details=NS(cached_tokens=0))
        return NS(id="exec-1", output=[call], output_text="", usage=usage)

    monkeypatch.setattr(OpenAIWorker, "_client", lambda self: None)
    monkeypatch.setattr(OpenAIWorker, "_create", fake_create)
    result = OpenAIWorker(check_cmd="true", executor_context="CERULEAN SECRET").run(
        "fix it", tmp_path, "gpt-5.4-mini-2026-03-17", 2, 60)
    assert result.ok and result.summary == "used direct context"
    assert result.breakdown["advisor"]["calls"] == 0
    assert len(seen) == 1


def test_openai_worker_blocks_edits_until_mandatory_consultation_succeeds(tmp_path, monkeypatch):
    import json
    from types import SimpleNamespace as NS
    from mas.workers import OpenAIWorker

    (tmp_path / "src").mkdir()
    target = tmp_path / "src" / "policylog.py"
    target.write_text("value = 1\n")
    executor_turn = 0

    def response(rid, output, text=""):
        return NS(id=rid, output=output, output_text=text,
                  usage=NS(input_tokens=10, output_tokens=5,
                           input_tokens_details=NS(cached_tokens=0)))

    def call(name, arguments, cid):
        return NS(type="function_call", name=name, arguments=json.dumps(arguments), call_id=cid)

    def fake_create(self, client, **kwargs):
        nonlocal executor_turn
        if kwargs["model"].startswith("gpt-5.5"):
            return response("advisor", [], "the private tuple")
        executor_turn += 1
        if executor_turn == 1:
            return response("e1", [call("edit_file", {"path": "src/policylog.py", "old_string": "1", "new_string": "2"}, "c1")])
        if executor_turn == 2:
            assert "consult ask_advisor" in kwargs["input"][0]["output"]
            assert target.read_text() == "value = 1\n"
            return response("e2", [call("ask_advisor", {"question": "profile?", "paths": []}, "c2")])
        if executor_turn == 3:
            return response("e3", [call("edit_file", {"path": "src/policylog.py", "old_string": "1", "new_string": "2"}, "c3")])
        return response("e4", [call("done", {"summary": "consulted then edited"}, "c4")])

    monkeypatch.setattr(OpenAIWorker, "_client", lambda self: None)
    monkeypatch.setattr(OpenAIWorker, "_create", fake_create)
    worker = OpenAIWorker(check_cmd="true", advisor_model="gpt-5.5-2026-04-23",
                          min_advice_calls=1, advisor_context="private")
    result = worker.run("implement it", tmp_path, "gpt-5.4-mini-2026-03-17", 8, 60)
    assert result.ok and target.read_text() == "value = 2\n"
    assert result.breakdown["advisor"]["checkpoint_satisfied"] is True


def test_demo_5_wires_fair_variants_and_external_quality_oracle(tmp_path):
    import json
    from mas.demo import ADVISOR_SCORE, ADVISOR_SMALL, ADVISOR_STRONG, init_demo
    from mas.workers import make_worker

    advised, items = init_demo(tmp_path / "advised", demo="5", variant="advised", base_config={})
    cfg = json.loads((advised / ".mas" / "config.json").read_text())
    assert [i.id for i in items] == ["authorize"] and items[0].worker_pref == "openai"
    assert items[0].meta["model"] == ADVISOR_SMALL and str(ADVISOR_SCORE) in items[0].check
    assert cfg["models"] == {"openai": [ADVISOR_SMALL]} and cfg["openai_advisor_model"] == ADVISOR_STRONG
    assert cfg["openai_min_advice_calls"] == 1 and cfg["openai_advisor_context_file"] == "demo_advisor/cerulean7.md"
    assert "authority rank" in make_worker("openai", cfg, check_cmd="true").advisor_context
    assert cfg["max_attempts"] == 1 and cfg["concurrency"] == 1

    direct, direct_items = init_demo(tmp_path / "direct", demo="5", variant="small-direct-context", base_config={})
    direct_cfg = json.loads((direct / ".mas" / "config.json").read_text())
    direct_worker = make_worker("openai", direct_cfg, check_cmd="true")
    assert direct_items[0].meta["model"] == ADVISOR_SMALL and direct_cfg["openai_advisor_model"] is None
    assert direct_cfg["openai_min_advice_calls"] == 0
    assert direct_cfg["openai_executor_context_file"] == "demo_advisor/cerulean7.md"
    assert "openai_advisor_context_file" not in direct_cfg
    assert "authority rank" in direct_worker.executor_context and direct_worker.advisor_context == ""

    strong, strong_items = init_demo(tmp_path / "strong", demo="5", variant="strong-alone", base_config={})
    strong_cfg = json.loads((strong / ".mas" / "config.json").read_text())
    assert strong_items[0].meta["model"] == ADVISOR_STRONG and strong_cfg["openai_advisor_model"] is None
    assert strong_cfg["openai_min_advice_calls"] == 0 and "openai_advisor_context_file" not in strong_cfg

    scored = subprocess.run([sys.executable, str(ADVISOR_SCORE), str(advised), "--json"], capture_output=True, text=True)
    quality = json.loads(scored.stdout)
    assert scored.returncode == 1 and quality["passed"] < quality["total"] and quality["total"] == 50
    assert quality["sections"]["public_contract"]["total"] == 30
    assert quality["sections"]["private_profile"]["total"] == 20


def test_demo_6_seeds_dead_lease_and_deterministic_recovery_graph(tmp_path):
    import json
    from mas.demo import init_demo

    dest, items = init_demo(tmp_path / "recovery", demo="6", base_config={})
    cfg = json.loads((dest / ".mas" / "config.json").read_text())
    assert [i.id for i in items] == ["crash-resume", "plan-recovery"]
    assert cfg["workers"] == ["chaos", "observer"] and cfg["concurrency"] == 4
    assert cfg["lease_seconds"] == 2 and cfg["models"]["chaos"] == ["fast-agent", "recovery-agent"]
    assert set(cfg["harnesses"]) == {"chaos", "observer"}
    board = SQLiteBoard(dest / ".mas" / "board.db")
    crashed = board.get("crash-resume")
    assert crashed.status == LEASED and crashed.attempts == 1 and crashed.lease_owner == "demo6-dead-orchestrator"
    stale = dest / ".mas" / "work" / "crash-resume-a1" / "artifacts" / "crash.txt"
    assert stale.read_text() == "partial-output-from-dead-worker\n"
    assert "fault_injected" in [e["kind"] for e in board.events("crash-resume")]
    plan = board.get("plan-recovery")
    assert plan.status == OPEN and plan.meta["spawn"]["after"][0]["meta"] == {"deps": "settled", "run_last": True}


def test_merge_paths_accept_directory_prefixes(repo):
    ws = Workspace(repo)
    p = ws.prepare("d-a1")
    (p / "src" / "a.py").write_text("x = 9\n")
    (p / "src" / "new.py").write_text("n = 1\n")
    (p / "tests").mkdir(); (p / "tests" / "test_x.py").write_text("def test(): pass\n")   # a worker 'fixing' the tests
    landed = ws.merge(p, ["src/"])
    assert sorted(landed) == ["src/a.py", "src/new.py"] and not (repo / "tests" / "test_x.py").exists()


def test_merge_directory_prefix_expands_wholly_untracked_directory(repo):
    ws = Workspace(repo)
    p = ws.prepare("new-tree-a1")
    (p / "result").mkdir()
    (p / "result" / "report.md").write_text("report\n")
    (p / "result" / "evidence.json").write_text("{}\n")
    assert sorted(ws.merge(p, ["result/"])) == ["result/evidence.json", "result/report.md"]
    assert (repo / "result" / "report.md").read_text() == "report\n"






def test_api_worker_protected_paths_and_claude_timeout_usage(tmp_path):
    from mas.workers import ApiWorker, estimate_claude_cost
    w = ApiWorker(check_cmd=None, protected=("tests/", "fixtures/", "PLAN.json"))
    (tmp_path / "tests").mkdir(); (tmp_path / "tests" / "t.py").write_text("x")
    assert "protected" in w._dispatch(tmp_path, "write_file", {"path": "tests/t.py", "content": "y"})
    assert "protected" in w._dispatch(tmp_path, "edit_file", {"path": "./fixtures/a/NOTES.md", "old_string": "a", "new_string": "b"})
    assert "protected" in w._dispatch(tmp_path, "write_file", {"path": "PLAN.json", "content": "{}"})
    assert w._dispatch(tmp_path, "write_file", {"path": "../escaped.txt", "content": "secret"}).startswith("ERROR:")
    assert not (tmp_path.parent / "escaped.txt").exists()
    assert w._dispatch(tmp_path, "write_file", {"path": "exports/x.py", "content": "ok"}) == "wrote exports/x.py"
    acc = {"input_tokens": 1000, "output_tokens": 2000, "cache_read_input_tokens": 100000, "cache_creation_input_tokens": 0}
    assert estimate_claude_cost("sonnet", acc) == round((1000 * 3 + 2000 * 15 + 100000 * 0.3) / 1e6, 4)
    assert estimate_claude_cost("mystery-model", acc) is None and estimate_claude_cost("haiku", {k: 0 for k in acc}) is None


# ------------------------------------------------------------------ planner output → items
def test_parse_plan_slugs_ids_and_resolves_dependencies():
    from mas.plan import parse_plan
    items = parse_plan({"items": [
        {"id": "flights", "title": "Find flights", "brief": "b", "check": "cmd:test -s flights.json", "merge_paths": ["flights.json"]},
        {"id": "hotels", "title": "Pick hotels", "brief": "b", "check": "human"},
        {"title": "Total the budget", "brief": "b", "check": "cmd:test -s budget.json", "depends_on": ["flights", "Pick hotels", "nonexistent"]},
        {"title": "no check here", "brief": "b"},
        {"id": "flights", "title": "Duplicate id", "brief": "b", "check": "human"},
    ]})
    assert [i.id for i in items] == ["flights", "hotels", "total-the-budget", "flights-4"]
    assert items[2].depends_on == ["flights", "hotels"]               # by id and by title; unknown dropped
    assert items[1].check == "human" and items[0].merge_paths == ["flights.json"]


def test_cli_edit_fixes_a_parked_contract_and_logs_it(repo, monkeypatch, capsys):
    from mas import cli
    monkeypatch.chdir(repo)
    cli.main(["init"])
    cli.main(["add", "Budget", "--id", "budget", "--brief", "b", "--check", "cmd:python -m pytest -q tests/t.py", "--merge", "budget.csv", "--max-attempts", "1"])
    board = SQLiteBoard(repo / ".mas" / "board.db")
    board.claim("w", 60, ["claude"]); board.fail("budget", "w", {"passed": False, "detail": "python: command not found"}, backoff_base=0.01)
    assert board.get("budget").status == PARKED                                                     # max_attempts=1 → the breaker opens at once
    cli.main(["edit", "budget", "--check", "cmd:/usr/bin/env python3 -m pytest -q tests/t.py", "--depends-on", ""])
    out = capsys.readouterr().out
    assert "edited budget: check" in out and "mas unpark budget" in out
    b2 = board.get("budget")
    assert b2.check.startswith("cmd:/usr/bin/env python3") and b2.status == PARKED and b2.attempts == 1 and b2.merge_paths == ["budget.csv"]
    kinds = [e["kind"] for e in board.events("budget")]
    assert kinds.count("added") == 1 and kinds[-1] == "edited"
    cli.main(["unpark", "budget"])
    assert board.get("budget").status == OPEN and board.get("budget").attempts == 0
