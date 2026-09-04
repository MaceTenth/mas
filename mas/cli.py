"""mas — the CLI.

  mas init                         create .mas/ (board + config) in the current project
  mas add "title" --brief ... --check "cmd:pytest tests/test_x.py" [--merge src/x.py] [--worker claude|codex|api|<harness>]
                  [--depends-on a,b,'review-*'] [--deps settled] [--model sonnet] [--schema shape.json] [--brief-file f.md]
  mas fanout 8 "Review as {persona}" --fleet claude,codex --persona ... --check "schema:votes/{id}.json" --merge "votes/{id}.json"
  mas plan "goal" [--with claude|codex] [--dry-run]     decompose a goal into items
  mas import-issues owner/repo [--label mas]            GitHub issues → items
  mas run [--workers claude,codex,api] [--concurrency 4] [--forever] [--github owner/repo] [--plain]
  mas watch                                             live view of a board another process is running
  mas status | mas show <id> | mas dashboard | mas events | mas lessons [--add "..."]
  mas unpark <id> | mas approve <id>
  mas supervise [--install-launchd]                     restart `mas run --forever` when it dies
  mas demo list | mas demo run 1 | mas demo run 2       demonstrations (all flags baked into the demo config)
  mas demo init <dir> [--demo N] [--force]              scaffold a demo without running it
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from . import __version__
from .board import SQLiteBoard, Item
from .workspace import Workspace

DEFAULT_CONFIG = {
    "workers": ["claude"],
    "concurrency": 4,
    "lease_seconds": 600,
    "heartbeat_seconds": 30,
    "max_turns": 20,
    "attempt_timeout_seconds": 900,
    "check_timeout_seconds": 300,
    "backoff_base_seconds": 5,
    "max_attempts": 3,
    "commit_on_merge": True,
    "share_lessons": True,
    "models": {"claude": ["haiku", "sonnet"], "codex": [None], "api": ["claude-haiku-4-5-20251001", "claude-sonnet-5"],
               "gemini": ["gemini-2.5-flash", "gemini-2.5-pro"]},      # known prices; 3.5-flash works too (cost unknown → tokens only)
    "claude_allowed_tools": "Read,Edit,MultiEdit,Write,Grep,Glob,Bash(python:*),Bash(python3:*),Bash(pytest:*),Bash(npm:*),Bash(node:*),Bash(git status:*),Bash(git diff:*)",
    "claude_bare": False,
    "codex_sandbox": "workspace-write",
    "codex_overrides": ["model_reasoning_effort=\"high\"", "mcp_servers={}"],   # workers run without personal MCP servers
    "harnesses": {},   # any other CLI agent with a headless mode — see `mas harnesses`
}


def find_root(start: Path | None = None) -> Path:
    p = (start or Path.cwd()).resolve()
    for q in [p, *p.parents]:
        if (q / ".mas").is_dir():
            return q
    return p


def load(root: Path):
    cfg_path = root / ".mas" / "config.json"
    cfg = dict(DEFAULT_CONFIG)
    if cfg_path.exists():
        cfg.update(json.loads(cfg_path.read_text()))
    board = SQLiteBoard(root / ".mas" / "board.db")
    return cfg, board


def cmd_init(a):
    root = Path(a.dir or ".").resolve()
    (root / ".mas").mkdir(parents=True, exist_ok=True)
    cfg_path = root / ".mas" / "config.json"
    if not cfg_path.exists():
        cfg_path.write_text(json.dumps(DEFAULT_CONFIG, indent=2))
    SQLiteBoard(root / ".mas" / "board.db")
    Workspace(root)
    print(f"initialized {root / '.mas'}  (board.db, config.json, work/)")


def _subst(text, vars_: dict):
    """Replace {i} {n} {kind} {id} {persona} {slug} literally — briefs contain JSON braces, so no str.format."""
    if text is None:
        return None
    for k, v in vars_.items():
        text = text.replace("{" + k + "}", str(v))
    return text


def _resolve_deps(board, spec: str | None) -> list[str]:
    """--depends-on a,b,vote-*  → ids; globs match items already on the board."""
    import fnmatch
    if not spec:
        return []
    ids = [i.id for i in board.list()]
    out = []
    for part in [p.strip() for p in spec.split(",") if p.strip()]:
        matched = fnmatch.filter(ids, part) if any(c in part for c in "*?[") else [part]
        if not matched:
            raise SystemExit(f"--depends-on {part!r} matches no item on the board")
        out += [m for m in matched if m not in out]
    return out


def _slug(title: str) -> str:
    import re
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:24] or "item"


def _item_from_args(a, cfg, board, vars_: dict | None = None) -> Item:
    vars_ = vars_ or {}
    brief = a.brief
    if getattr(a, "brief_file", None):
        brief = Path(a.brief_file).read_text()
    if brief is None:
        brief = sys.stdin.read() if not sys.stdin.isatty() else a.title
    meta = {}
    for kv in (getattr(a, "meta", None) or []):
        k, _, v = kv.partition("=")
        try:
            meta[k] = json.loads(v)
        except Exception:
            meta[k] = v
    if getattr(a, "schema", None):
        meta["schema"] = json.loads(Path(a.schema).read_text())
    if getattr(a, "model", None):
        meta["model"] = a.model
    if getattr(a, "deps", None):
        meta["deps"] = a.deps
    worker = _subst(getattr(a, "worker", None), vars_)
    known = {"claude", "codex", "api", "gemini", *((cfg.get("harnesses") or {}).keys())}
    if worker and worker not in known:
        raise SystemExit(f"unknown worker {worker!r} — built-in: claude, codex, api; configured: {', '.join(sorted(known - {'claude', 'codex', 'api'})) or 'none'} (mas harnesses)")
    return Item(id=_subst(a.id, vars_) or "", title=_subst(a.title, vars_), brief=_subst(brief, vars_),
                check=_subst(a.check, vars_) or "human", merge_paths=[_subst(m, vars_) for m in (a.merge or [])],
                priority=a.priority, max_attempts=a.max_attempts or cfg["max_attempts"], worker_pref=worker,
                depends_on=_resolve_deps(board, _subst(getattr(a, "depends_on", None), vars_)), meta=meta)


def cmd_add(a):
    root = find_root(); cfg, board = load(root)
    item = _item_from_args(a, cfg, board)
    board.add(item)
    extra = (f" · depends_on={item.depends_on}" if item.depends_on else "") + (f" · model={item.meta['model']}" if item.meta.get("model") else "")
    print(f"added {item.id} · {item.title} · check={item.check} · worker={item.worker_pref or 'any'}{extra}")


def cmd_fanout(a):
    """N independent copies of one item — the bulkhead pattern from the CLI.

    Placeholders in title/brief/check/merge/id/worker: {i} {n} {kind} {id} {persona} {slug}.
    Kinds rotate through --fleet, personas through --persona (repeatable)."""
    root = find_root(); cfg, board = load(root)
    fleet = [k.strip() for k in (a.fleet or "").split(",") if k.strip()] or [None]
    personas = a.persona or [""]
    slug = a.slug or _slug(a.title)
    ids = []
    for i in range(1, a.n + 1):
        kind = fleet[(i - 1) % len(fleet)]
        persona = personas[(i - 1) // max(1, len(fleet)) % len(personas)] if len(personas) > 1 else personas[0]
        iid = (a.id or "{slug}-{i}" + ("-{kind}" if kind else ""))
        vars_ = {"i": i, "n": a.n, "kind": kind or "", "persona": persona, "slug": slug}
        vars_["id"] = _subst(iid, vars_)
        ns = argparse.Namespace(**{**vars(a), "id": vars_["id"], "worker": a.worker or kind})
        item = _item_from_args(ns, cfg, board, vars_)
        board.add(item); ids.append(item.id)
    print(f"added {len(ids)} items: {', '.join(ids)}")
    print(f"depend on them with:  --depends-on '{slug}-*'")


def cmd_plan(a):
    from .plan import plan
    root = find_root(); cfg, board = load(root)
    items = plan(a.goal, root, kind=a.with_, n=a.n, model=a.model)
    if not items:
        print("planner returned no items"); return
    for it in items:
        print(f"  {it.id}  {it.title}\n      check: {it.check}  merge: {it.merge_paths or '(changed files)'}")
    if a.dry_run:
        print(f"\n{len(items)} items (dry run — not added)"); return
    for it in items:
        it.max_attempts = cfg["max_attempts"]; board.add(it)
    print(f"\nadded {len(items)} items to the board")


def cmd_import(a):
    from .github import import_issues
    root = find_root(); cfg, board = load(root)
    items = import_issues(board, a.repo, label=a.label, default_check=a.default_check, max_attempts=cfg["max_attempts"])
    for it in items:
        print(f"  {it.id}  {it.title}  check={it.check}")
    print(f"imported {len(items)} issue(s) from {a.repo}")


def cmd_run(a, root: Path | None = None):
    from .orchestrator import Orchestrator
    root = root or find_root(); cfg, board = load(root)
    kinds = [k.strip() for k in (a.workers or ",".join(cfg["workers"])).split(",") if k.strip()]
    harnesses = cfg.get("harnesses") or {}
    for k in kinds:
        if k in harnesses:
            exe = str(harnesses[k].get("cmd", [""])[0])
            if exe and "/" not in exe and not shutil_which(exe):
                raise SystemExit(f"harness '{k}' requested but `{exe}` is not on PATH")
            continue
        if k not in ("claude", "codex", "api", "gemini"):
            raise SystemExit(f"unknown worker kind: {k} — built-in: claude, codex, api, gemini; configured harnesses: {', '.join(harnesses) or 'none'} (see `mas harnesses`)")
        if k in ("claude", "codex") and not shutil_which(k):
            raise SystemExit(f"worker '{k}' requested but `{k}` is not on PATH")
        if k == "api" and not os.environ.get("ANTHROPIC_API_KEY"):
            raise SystemExit("worker 'api' needs ANTHROPIC_API_KEY in the environment")
        if k == "gemini" and not os.environ.get("GEMINI_API_KEY"):
            raise SystemExit("worker 'gemini' needs GEMINI_API_KEY in the environment (pip install google-genai)")
    if a.max_turns: cfg["max_turns"] = a.max_turns
    if a.lease: cfg["lease_seconds"] = a.lease
    github = None
    gh_repo = a.github or cfg.get("github")
    if gh_repo:
        from .github import GitHubMirror
        github = GitHubMirror(gh_repo, labels=cfg.get("github_labels") or [])
    live = sys.stdout.isatty() and not a.plain
    t0 = time.time()
    if live:
        from .ui import LiveUI, print_summary
        ui = LiveUI(board, title=f"run · {root.name}")
        orch = Orchestrator(board, Workspace(root), cfg, kinds, concurrency=a.concurrency or cfg["concurrency"], github=github,
                            log=ui.status)
        ui.cfg.update(orch.describe_config())
        with ui:
            orch.run(forever=a.forever, max_items=a.max_items)
        print_summary(board, t0, orch.interrupted)
    else:
        def stamp(m):
            try:
                print(f"{time.strftime('%H:%M:%S')} {m}", flush=True)
            except BrokenPipeError:          # `mas run | head` — the reader left; keep orchestrating
                pass
        orch = Orchestrator(board, Workspace(root), cfg, kinds, concurrency=a.concurrency or cfg["concurrency"], github=github,
                            log=stamp, activity_log=None if a.quiet else stamp)
        orch.run(forever=a.forever, max_items=a.max_items)
    if orch.interrupted:
        raise SystemExit(130)


def cmd_watch(a):
    from .ui import LiveUI
    root = find_root(); cfg, board = load(root)
    last = [e for e in board.events(limit=500) if e["kind"] == "run_started"]
    ui = LiveUI(board, cfg=last[-1]["data"] if last else {"workers": cfg["workers"], "concurrency": cfg["concurrency"],
                "lease_s": cfg["lease_seconds"], "max_turns": cfg["max_turns"], "models": cfg["models"], "max_attempts": cfg["max_attempts"]},
                title=f"watch · {root.name}")
    ui.status("watching the board (read-only) — Ctrl-C to leave; the run keeps going")
    try:
        with ui:
            while True:
                time.sleep(1)
    except KeyboardInterrupt:
        pass


def cmd_harnesses(a):
    """List worker kinds; `mas harnesses add <preset|name>` writes one into .mas/config.json."""
    from .workers import HARNESS_PRESETS
    root = find_root(); cfg, _ = load(root)
    cfg_path = root / ".mas" / "config.json"
    hs = dict(cfg.get("harnesses") or {})
    if a.action == "add":
        name = a.name
        if not name:
            raise SystemExit(f"usage: mas harnesses add <preset>   presets: {', '.join(HARNESS_PRESETS)}")
        spec = HARNESS_PRESETS.get(name)
        if spec is None:
            raise SystemExit(f"no preset {name!r}. Presets: {', '.join(HARNESS_PRESETS)}. For anything else, add a 'harnesses' block to {cfg_path} (see below).")
        spec = {k: v for k, v in spec.items() if not k.startswith("_")}
        if a.cmd:
            spec["cmd"] = a.cmd
        hs[name] = spec
        stored = json.loads(cfg_path.read_text()) if cfg_path.exists() else {}
        stored["harnesses"] = hs
        if name not in (stored.get("models") or {}):
            stored.setdefault("models", dict(cfg.get("models") or {}))[name] = [None]
        cfg_path.write_text(json.dumps(stored, indent=2))
        print(f"added harness '{name}' → {cfg_path}\n  {' '.join(spec['cmd'])}\n  run it:  mas run --workers {name}   or mix:  mas run --workers claude,{name}")
        return
    print("built-in workers:   claude (claude -p)   codex (codex exec)   api (Anthropic Messages API loop)   gemini (Gemini API loop, GEMINI_API_KEY)")
    print("configured harnesses:" if hs else "configured harnesses: none")
    for k, spec in hs.items():
        exe = str(spec.get("cmd", ["?"])[0]); on = "on PATH" if shutil_which(exe) else "NOT on PATH"
        print(f"  {k:<10} {' '.join(spec.get('cmd', []))}   [{on}]")
    print("\npresets (mas harnesses add <name>):")
    for k, spec in HARNESS_PRESETS.items():
        exe = spec["cmd"][0]; on = "on PATH" if shutil_which(exe) else "not on PATH"
        print(f"  {k:<10} [{on}]  {spec.get('_about', '')}")
    print("\nanything else: any CLI with a headless mode — describe it in .mas/config.json:")
    print(json.dumps({"harnesses": {"mybot": {"cmd": ["mybot", "--non-interactive", "--prompt", "{prompt}", "--model", "{model}"],
                                             "prompt_via": "arg", "summary": "stdout_tail", "activity": "lines"}}}, indent=2))
    print("placeholders: {prompt} {prompt_file} {cwd} {model} {max_turns} {out_file}  ·  models per kind under \"models\"")


def _demo_run_variants(a, spec, base: Path, fleet):
    """Demo 5: each variant is its own project (board, repo, issues) under <base>/<variant>; then compare."""
    from .demo import init_demo
    variants = [v.strip() for v in (a.variants or ",".join(spec["variants"])).split(",") if v.strip()]
    base.mkdir(parents=True, exist_ok=True)
    extra = {}
    if spec.get("generate"):
        extra = {"hidden": base / "hidden", "deadline": getattr(a, "deadline", None) or 600, "seed": getattr(a, "seed", None) or 7}
    for v in variants:
        dest = base / v
        force = dest.exists() and any(dest.iterdir())
        dest, items = init_demo(dest, force=force, demo=a.demo, base_config=DEFAULT_CONFIG, fleet=fleet, variant=v, github=a.github, **extra)
        conf = spec["config"](sys.executable, fleet, variant=v, github=a.github, **extra)
        banner = f"{spec['name']} · variant {v} · {len(items)} items · workers {','.join(conf['workers'])}" + (f" · issues → {a.github}" if a.github else "")
        if sys.stdout.isatty() and not a.plain:
            from .ui import console
            console.print(f"\n[bold]{banner}[/bold]\n[grey50]project {dest}[/grey50]\n")
        else:
            print(f"\n=== {banner}\nproject {dest}", flush=True)
        ns = argparse.Namespace(workers=None, concurrency=None, forever=False, max_items=a.max_items, max_turns=None,
                                lease=None, github=None, plain=a.plain, quiet=getattr(a, "quiet", False))
        cmd_run(ns, root=dest)
    if not spec.get("compare"):
        return
    r = subprocess.run([sys.executable, str(spec["compare"]), str(base)], capture_output=True, text=True)
    print(r.stdout or r.stderr)
    print(f"\ncomparison → {base / 'comparison.md'}")


def _rich() -> bool:
    return sys.stdout.isatty() and not os.environ.get("MAS_PLAIN")


def cmd_status(a):
    root = find_root(); _, board = load(root)
    if _rich():
        from .ui import print_status; print_status(board)
    else:
        from .views import status_table; print(status_table(board, a.filter))


def cmd_show(a):
    from .views import show_item
    root = find_root(); _, board = load(root)
    if _rich():
        from .ui import console, print_events
        text = show_item(board, a.id)
        console.print(text.split("EVENTS")[0].rstrip(), highlight=False, markup=False)
        console.print("[bold]EVENTS[/bold]")
        print_events(board, 60, item_id=a.id)
    else:
        print(show_item(board, a.id))


def cmd_dashboard(a):
    root = find_root(); _, board = load(root)
    if _rich():
        from .ui import print_summary, print_status
        first = board.events(limit=1)
        print_status(board)
        print_summary(board, first[0]["ts"] if first else time.time())
    else:
        from .views import dashboard; print(dashboard(board))


def cmd_events(a):
    root = find_root(); _, board = load(root)
    if _rich():
        from .ui import print_events; print_events(board, a.n, item_id=a.item)
    else:
        from .views import events_tail; print(events_tail(board, a.n))


def cmd_lessons(a):
    root = find_root(); _, board = load(root)
    if a.add:
        board.add_lesson(a.add); print("lesson recorded"); return
    for l in board.lessons(a.n):
        print(f"- {l['text']}")


def cmd_unpark(a):
    root = find_root(); _, board = load(root)
    print("reopened" if board.unpark(a.id, a.note or "") else f"{a.id} is not parked/awaiting")


def cmd_approve(a):
    root = find_root(); _, board = load(root)
    print("approved → done" if board.approve(a.id, a.note or "") else f"{a.id} is not awaiting approval")


def cmd_supervise(a):
    root = find_root()
    if a.install_launchd:
        label = f"local.mas.{root.name}"
        plist = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>{label}</string>
  <key>ProgramArguments</key><array><string>{sys.argv[0]}</string><string>run</string><string>--forever</string></array>
  <key>WorkingDirectory</key><string>{root}</string>
  <key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>{root}/.mas/supervisor.log</string>
  <key>StandardErrorPath</key><string>{root}/.mas/supervisor.err</string>
</dict></plist>"""
        dest = Path.home() / "Library" / "LaunchAgents" / f"{label}.plist"
        dest.write_text(plist)
        print(f"wrote {dest}\nload with:   launchctl load {dest}\nunload with: launchctl unload {dest}")
        return
    # in-process supervisor: restart `mas run --forever` whenever it exits
    backoff = 2.0
    while True:
        started = time.time()
        print(f"{time.strftime('%H:%M:%S')} supervisor: starting `mas run --forever`", flush=True)
        r = subprocess.run([sys.argv[0], "run", "--forever"], cwd=root)
        ran = time.time() - started
        backoff = 2.0 if ran > 120 else min(backoff * 2, 60)
        print(f"{time.strftime('%H:%M:%S')} supervisor: run exited ({r.returncode}) after {int(ran)}s — restarting in {int(backoff)}s", flush=True)
        time.sleep(backoff)


DEMO_DIR = Path.home() / "mas-demo"


def cmd_demo(a):
    from .demo import init_demo, DEMOS
    fleet = [k.strip() for k in a.fleet.split(",")] if getattr(a, "fleet", None) else None
    dest, items = init_demo(Path(a.dir), force=a.force, demo=a.demo, base_config=DEFAULT_CONFIG, fleet=fleet)
    spec = DEMOS[str(a.demo)]
    conf = spec["config"](sys.executable, fleet) if callable(spec["config"]) else spec["config"]
    print(f"{spec['name']} → {dest}\n{len(items)} items on the board\n"
          f"config: workers={','.join(conf['workers'])} concurrency={conf['concurrency']} lease={conf['lease_seconds']}s\n")
    print(f"  cd {dest}\n  mas status\n  mas run          # flags come from .mas/config.json\n  mas watch        # in a second terminal\n  mas dashboard")


def cmd_demo_list(a):
    from .demo import DEMOS
    for k, spec in DEMOS.items():
        conf = spec["config"](sys.executable, None) if callable(spec["config"]) else spec["config"]
        print(f"mas demo run {k}   {spec['name']}\n    {spec['tagline']}\n    show: {spec['show']}\n"
              f"    config: {json.dumps({kk: vv for kk, vv in conf.items() if kk in ('workers', 'concurrency', 'lease_seconds')})}\n")


def cmd_demo_run(a):
    """Reset the demo directory, then run it — no flags needed; the demo's config carries them."""
    from .demo import init_demo, DEMOS
    spec = DEMOS.get(str(a.demo))
    if spec is None:
        raise SystemExit(f"unknown demo {a.demo!r} — see `mas demo list`")
    dest = Path(a.dir or DEMO_DIR)
    fleet = [k.strip() for k in a.fleet.split(",")] if getattr(a, "fleet", None) else None
    if spec.get("variants"):
        return _demo_run_variants(a, spec, dest, fleet)
    force = dest.exists() and any(dest.iterdir())          # only a directory with .mas/ is ever wiped (init_demo checks)
    dest, items = init_demo(dest, force=force, demo=a.demo, base_config=DEFAULT_CONFIG, fleet=fleet)
    conf = spec["config"](sys.executable, fleet) if callable(spec["config"]) else spec["config"]
    for k in conf["workers"]:
        if k in ("claude", "codex") and not shutil_which(k):
            raise SystemExit(f"{spec['name']} needs `{k}` on PATH")
    if sys.stdout.isatty() and not a.plain:
        from .ui import console
        console.print(f"[bold]{spec['name']}[/bold] · [grey70]{spec['tagline']}[/grey70]")
        console.print(f"[grey50]project {dest} · {len(items)} items · watch from another terminal: cd {dest} && mas watch[/grey50]\n")
    else:
        print(f"{spec['name']} · {spec['tagline']}\nproject {dest} · {len(items)} items", flush=True)
    ns = argparse.Namespace(workers=None, concurrency=None, forever=False, max_items=a.max_items, max_turns=None,
                            lease=None, github=None, plain=a.plain, quiet=getattr(a, "quiet", False))
    cmd_run(ns, root=dest)


def shutil_which(name):
    from shutil import which
    return which(name)


def main(argv=None):
    p = argparse.ArgumentParser(prog="mas", description="mas — a multi-agent environment (board · compartments · workers · gate · log)")
    p.add_argument("--version", action="version", version=f"mas {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("init", help="create .mas/ in a project"); s.add_argument("dir", nargs="?"); s.set_defaults(fn=cmd_init)
    def item_args(s):
        s.add_argument("title"); s.add_argument("--brief"); s.add_argument("--brief-file", help="read the brief from a file (stdin also works)")
        s.add_argument("--check", help='"cmd:<shell>" | "schema:<path>" | "human" | "none"')
        s.add_argument("--schema", help="JSON schema file (required keys + types) for a schema: check")
        s.add_argument("--merge", action="append", help="file allowed to land on main (repeatable)"); s.add_argument("--id")
        s.add_argument("--priority", type=int, default=0); s.add_argument("--max-attempts", type=int)
        s.add_argument("--worker", help="claude | codex | api | any configured harness")
        s.add_argument("--model", help="pin a model for this item (overrides the worker's tiers)")
        s.add_argument("--depends-on", help="comma list of item ids; globs allowed, e.g. 'review-*'")
        s.add_argument("--deps", choices=["done", "settled"], help="dependency policy: done (default) or settled (parked counts)")
        s.add_argument("--meta", action="append", help="extra meta key=value (repeatable; value parsed as JSON when possible)")
    s = sub.add_parser("add", help="add an item to the board"); item_args(s); s.set_defaults(fn=cmd_add)
    s = sub.add_parser("fanout", help="add N independent copies of an item (placeholders: {i} {n} {kind} {id} {persona} {slug})")
    s.add_argument("n", type=int); item_args(s)
    s.add_argument("--fleet", help="rotate worker kinds, e.g. claude,codex"); s.add_argument("--persona", action="append", help="rotate personas (repeatable)")
    s.add_argument("--slug", help="id prefix (default from the title)"); s.set_defaults(fn=cmd_fanout)
    s = sub.add_parser("plan", help="decompose a goal into items"); s.add_argument("goal"); s.add_argument("--with", dest="with_", default="claude", choices=["claude", "codex"])
    s.add_argument("--n", type=int, default=12); s.add_argument("--model"); s.add_argument("--dry-run", action="store_true"); s.set_defaults(fn=cmd_plan)
    s = sub.add_parser("import-issues", help="GitHub issues → items"); s.add_argument("repo"); s.add_argument("--label"); s.add_argument("--default-check", default="human"); s.set_defaults(fn=cmd_import)
    s = sub.add_parser("run", help="run the orchestrator"); s.add_argument("--workers", help="comma list: claude,codex,api"); s.add_argument("--concurrency", type=int)
    s.add_argument("--forever", action="store_true"); s.add_argument("--max-items", type=int); s.add_argument("--max-turns", type=int); s.add_argument("--lease", type=float, help="lease seconds")
    s.add_argument("--github", help="owner/repo to mirror verdicts to")
    s.add_argument("--plain", action="store_true", help="line logs instead of the live view (auto when not a TTY)")
    s.add_argument("--quiet", action="store_true", help="plain mode: hide worker tool-call lines"); s.set_defaults(fn=cmd_run)
    s = sub.add_parser("watch", help="live view of the board (read-only)"); s.set_defaults(fn=cmd_watch)
    s = sub.add_parser("harnesses", help="worker kinds: built-ins + harnesses from config; `add <preset>` to enable one")
    s.add_argument("action", nargs="?", choices=["list", "add"], default="list")
    s.add_argument("name", nargs="?", help="preset to write into .mas/config.json (hermes, gemini, opencode, aider)")
    s.add_argument("--cmd", nargs="+", help="override the preset's command template"); s.set_defaults(fn=cmd_harnesses)
    s = sub.add_parser("status", help="board table"); s.add_argument("filter", nargs="?"); s.set_defaults(fn=cmd_status)
    s = sub.add_parser("show", help="one item + its events"); s.add_argument("id"); s.set_defaults(fn=cmd_show)
    s = sub.add_parser("dashboard", help="aggregate view"); s.set_defaults(fn=cmd_dashboard)
    s = sub.add_parser("events", help="event log tail"); s.add_argument("-n", type=int, default=30); s.add_argument("--item"); s.set_defaults(fn=cmd_events)
    s = sub.add_parser("lessons", help="shared lessons"); s.add_argument("--add"); s.add_argument("-n", type=int, default=12); s.set_defaults(fn=cmd_lessons)
    s = sub.add_parser("unpark", help="reopen a parked item"); s.add_argument("id"); s.add_argument("--note"); s.set_defaults(fn=cmd_unpark)
    s = sub.add_parser("approve", help="approve an item awaiting a human"); s.add_argument("id"); s.add_argument("--note"); s.set_defaults(fn=cmd_approve)
    s = sub.add_parser("supervise", help="keep `mas run --forever` alive"); s.add_argument("--install-launchd", action="store_true"); s.set_defaults(fn=cmd_supervise)
    d = sub.add_parser("demo", help="demonstrations: `mas demo list`, `mas demo run 1`"); ds = d.add_subparsers(dest="demo_cmd", required=True)
    dl = ds.add_parser("list", help="list demos"); dl.set_defaults(fn=cmd_demo_list)
    dr = ds.add_parser("run", help="reset ~/mas-demo and run a demo with its baked-in config"); dr.add_argument("demo", nargs="?", default="1", help="1 | 2 | 3 | 4")
    dr.add_argument("--fleet", help="demos 3/4: reviewer harnesses, e.g. claude,codex (default) or claude")
    dr.add_argument("--variants", help="variant demos: comma list of variants to run")
    dr.add_argument("--github", help="mirror every item to issues in owner/repo (labels mas, demoN-<variant>)")
    dr.add_argument("--deadline", type=int, help=argparse.SUPPRESS); dr.add_argument("--seed", type=int, help=argparse.SUPPRESS)
    dr.add_argument("--dir", help=f"project directory (default {Path.home() / 'mas-demo'})"); dr.add_argument("--plain", action="store_true")
    dr.add_argument("--quiet", action="store_true", help="plain mode: hide worker tool-call lines")
    dr.add_argument("--max-items", type=int, help=argparse.SUPPRESS); dr.set_defaults(fn=cmd_demo_run)
    di = ds.add_parser("init", help="scaffold a demo without running it"); di.add_argument("dir"); di.add_argument("--demo", default="1"); di.add_argument("--fleet")
    di.add_argument("--force", action="store_true", help="reset an existing demo directory (must contain .mas/)")
    di.set_defaults(fn=cmd_demo)

    a = p.parse_args(argv)
    a.fn(a)


if __name__ == "__main__":
    main()
