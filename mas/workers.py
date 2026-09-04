"""Workers: disposable, interchangeable, one item each.

  claude  → `claude -p` (Claude Code headless)
  codex   → `codex exec --sandbox workspace-write --json` (OpenAI Codex CLI ≥ 0.150)
  api     → a minimal tool loop on the Anthropic Messages API (no harness needed)
  gemini  → the same tool loop on the Gemini API (google-genai; GEMINI_API_KEY) — cheap Flash models
  <any>   → ExecWorker: a harness described in config ("harnesses": {...}) — any CLI
            with a headless mode: a command template, how the prompt goes in, how
            the summary comes out, optionally how to read its event stream

All return the same WorkerResult. None is trusted: the gate verifies.

THE WORKER CONTRACT (what makes mas pluggable)
  run(prompt, cwd, model, max_turns, timeout_s, on_activity) -> WorkerResult
  - prompt: the brief + the check the orchestrator will run (text)
  - cwd:    an isolated working copy the worker may change freely
  - the worker exits; whatever it changed in cwd is the result. Nothing else is read.
  - WorkerResult.ok is the worker's CLAIM, never the verdict — the gate re-runs the check.
  So a harness qualifies if it (1) runs non-interactively, (2) takes a prompt,
  (3) works in a given directory, (4) exits. Model choice, cost and a machine-readable
  event stream are optional niceties for the live view.
"""
from __future__ import annotations

import json
import os
import re
import shlex
import signal
import subprocess
import tempfile
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class WorkerResult:
    ok: bool                     # the worker finished and claims success (NOT verified)
    summary: str = ""
    turns: Optional[int] = None
    cost_usd: Optional[float] = None
    error: Optional[str] = None
    seconds: float = 0.0
    tokens: Optional[int] = None          # total tokens when the harness reports them (codex has no $ cost on a ChatGPT plan)
    raw: dict = field(default_factory=dict)

    def as_dict(self):
        return {"ok": self.ok, "summary": self.summary[:800], "turns": self.turns, "cost_usd": self.cost_usd,
                "error": self.error, "seconds": round(self.seconds, 1), "tokens": self.tokens}


PROMPT_TEMPLATE = """You are one worker in a multi-agent system. You own exactly ONE task, in an isolated working copy. Other workers handle other tasks; do not touch anything outside your task's scope.

TASK: {title}

{brief}

RULES
- Work only inside this directory. Do not modify tests or verification files.
- Your work will be verified by the orchestrator running: {check}
  Run that yourself before finishing; do not report success unless it passes.
- Keep changes minimal and focused on the task.
{lessons}"""


def build_prompt(title: str, brief: str, check: str, lessons: list[str] | None = None) -> str:
    ls = ""
    if lessons:
        ls = "\nLESSONS FROM EARLIER WORKERS (short, may help):\n" + "\n".join(f"- {l}" for l in lessons[-6:]) + "\n"
    human_check = check[4:] if check.startswith("cmd:") else check
    return PROMPT_TEMPLATE.format(title=title, brief=brief, check=human_check, lessons=ls)


# --------------------------------------------------------------------------
# child-process registry: the orchestrator's graceful stop kills every live worker
STOP = threading.Event()
_CHILDREN: set = set()
_LOCK = threading.Lock()


def _run(cmd: list, cwd: Optional[Path], timeout_s: int) -> subprocess.CompletedProcess:
    """subprocess.run, but the child gets its own process group and is registered
    so kill_children() can reach it (and everything it spawned)."""
    p = subprocess.Popen(cmd, cwd=cwd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True)
    with _LOCK:
        _CHILDREN.add(p)
    try:
        out, err = p.communicate(timeout=timeout_s)
    except subprocess.TimeoutExpired:
        _kill(p)
        raise
    finally:
        with _LOCK:
            _CHILDREN.discard(p)
    return subprocess.CompletedProcess(cmd, p.returncode, out, err)


def _kill(p: subprocess.Popen):
    try:
        os.killpg(p.pid, signal.SIGTERM)
    except (ProcessLookupError, PermissionError):
        return
    try:
        p.wait(timeout=3)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(p.pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass


def _stream(cmd: list, cwd: Optional[Path], timeout_s: int, on_line, env: Optional[dict] = None,
            stdin_text: Optional[str] = None) -> subprocess.CompletedProcess:
    """Like _run, but hands every stdout line to on_line as it arrives (live worker activity)."""
    p = subprocess.Popen(cmd, cwd=cwd, stdin=subprocess.PIPE if stdin_text is not None else subprocess.DEVNULL,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True, env=env)
    if stdin_text is not None:
        try:
            p.stdin.write(stdin_text); p.stdin.close()
        except (BrokenPipeError, OSError):
            pass
    with _LOCK:
        _CHILDREN.add(p)
    err: list = []
    threading.Thread(target=lambda: err.extend(p.stderr), daemon=True).start()
    fired = threading.Event()
    timer = threading.Timer(timeout_s, lambda: (fired.set(), _kill(p)))
    timer.start()
    try:
        for line in p.stdout:
            try:
                on_line(line)
            except Exception:
                pass
        p.wait()
    finally:
        timer.cancel()
        with _LOCK:
            _CHILDREN.discard(p)
    if fired.is_set():
        raise subprocess.TimeoutExpired(cmd, timeout_s)
    return subprocess.CompletedProcess(cmd, p.returncode, "", "".join(err))


def summarize_tool(name: str, inp: dict, cwd: Optional[Path] = None) -> str:
    """One short line for a tool call, for the live view."""
    def rel(v):
        try:
            return str(Path(str(v)).resolve().relative_to(Path(cwd).resolve())) if cwd else str(v)
        except Exception:
            return str(v)
    for k in ("file_path", "path", "notebook_path"):
        if k in inp:
            extra = ""
            if name in ("Grep", "grep") and inp.get("pattern"):
                extra = f" /{inp['pattern']}/"
            return rel(inp[k]) + extra
    if "command" in inp:
        return str(inp["command"])[:120]
    if "pattern" in inp:
        return f"/{inp['pattern']}/" + (f" in {rel(inp['path'])}" if inp.get("path") else "")
    if "summary" in inp:
        return str(inp["summary"])[:120]
    return json.dumps(inp, default=str)[:100]


def kill_children() -> int:
    """Stop every live worker (CLI process groups; the API loop checks STOP between turns)."""
    STOP.set()
    with _LOCK:
        procs = list(_CHILDREN)
    for p in procs:
        _kill(p)
    return len(procs)


CLAUDE_LIST_PRICES = {  # $ per 1M tokens: input, output, cache read, cache write — used ONLY when the CLI did not report a cost
    "haiku": (1.0, 5.0, 0.10, 1.25), "sonnet": (3.0, 15.0, 0.30, 3.75), "opus": (15.0, 75.0, 1.50, 18.75),
}


def estimate_claude_cost(model: Optional[str], acc: dict) -> Optional[float]:
    key = next((k for k in CLAUDE_LIST_PRICES if k in (model or "")), None)
    if not key or not any(acc.values()):
        return None
    i, o, cr, cw = CLAUDE_LIST_PRICES[key]
    return round((acc["input_tokens"] * i + acc["output_tokens"] * o + acc["cache_read_input_tokens"] * cr + acc["cache_creation_input_tokens"] * cw) / 1e6, 4)


# --------------------------------------------------------------------------
class ClaudeCliWorker:
    name = "claude"

    def __init__(self, allowed_tools: str, bare: bool = False, check_cmd: Optional[str] = None):
        self.bare = bare
        # always allow the item's own check command (e.g. "/path/to/python -m pytest tests/x.py -q"),
        # so the worker can verify itself before claiming done — the gate re-runs it regardless.
        extra = []
        if check_cmd:
            toks = shlex.split(check_cmd)
            prefix = " ".join(toks[:3]) if len(toks) >= 3 else check_cmd
            extra = [f"Bash({prefix}:*)", f"Bash({check_cmd})"]
        self.allowed_tools = ",".join([allowed_tools, *extra]) if extra else allowed_tools

    def run(self, prompt: str, cwd: Path, model: Optional[str], max_turns: int, timeout_s: int, on_activity=None) -> WorkerResult:
        cmd = ["claude", "-p", prompt, "--output-format", "stream-json", "--verbose", "--max-turns", str(max_turns),
               "--permission-mode", "acceptEdits", "--allowedTools", self.allowed_tools]
        if model:
            cmd += ["--model", model]
        if self.bare:
            cmd.append("--bare")
        data: dict = {}
        acc = {"input_tokens": 0, "output_tokens": 0, "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0}

        def on_line(line: str):
            line = line.strip()
            if not line:
                return
            d = json.loads(line)
            t = d.get("type")
            if t == "assistant":
                u = (d.get("message") or {}).get("usage") or {}
                for k in acc:
                    acc[k] += int(u.get(k) or 0)
            if t == "assistant" and on_activity:
                for b in d.get("message", {}).get("content", []) or []:
                    if b.get("type") == "tool_use":
                        on_activity(b.get("name", "tool"), summarize_tool(b.get("name", ""), b.get("input") or {}, cwd))
                    elif b.get("type") == "text" and (b.get("text") or "").strip():
                        on_activity("💬", b["text"].strip().replace("\n", " ")[:140])
            elif t == "result":
                data.update(d)

        t0 = time.monotonic()
        try:
            r = _stream(cmd, cwd, timeout_s, on_line)
        except subprocess.TimeoutExpired:
            toks = sum(acc.values()) or None
            return WorkerResult(False, error=f"timeout after {timeout_s}s (work on disk is still gated and may land)", seconds=time.monotonic() - t0,
                                tokens=toks, cost_usd=estimate_claude_cost(model, acc), raw={"usage": acc, "cost_estimated": True})
        secs = time.monotonic() - t0
        if STOP.is_set():
            return WorkerResult(False, error="interrupted (orchestrator stopping)", seconds=secs)
        if r.returncode != 0 and not data:
            return WorkerResult(False, error=(r.stderr or "")[-800:], seconds=secs, tokens=sum(acc.values()) or None,
                                cost_usd=estimate_claude_cost(model, acc), raw={"usage": acc, "cost_estimated": True})
        u = data.get("usage") or {}
        toks = sum(int(u.get(k) or 0) for k in ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")) or None
        return WorkerResult(ok=not data.get("is_error", False), summary=str(data.get("result", ""))[:2000],
                            turns=data.get("num_turns"), cost_usd=data.get("total_cost_usd"), seconds=secs, tokens=toks,
                            raw={k: data.get(k) for k in ("session_id", "duration_ms", "is_error", "stop_reason")})


# --------------------------------------------------------------------------
class CodexCliWorker:
    name = "codex"

    def __init__(self, sandbox: str = "workspace-write", overrides: Optional[list] = None, json_events: bool = True, ephemeral: bool = True):
        self.sandbox = sandbox             # read-only | workspace-write | danger-full-access
        self.overrides = overrides or []   # `-c key=value` config overrides (e.g. reasoning effort, mcp_servers={})
        self.json_events = json_events     # `codex exec --json` → live activity
        self.ephemeral = ephemeral         # don't persist worker sessions under ~/.codex

    def run(self, prompt: str, cwd: Path, model: Optional[str], max_turns: int, timeout_s: int, on_activity=None) -> WorkerResult:
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
            last = f.name
        cmd = ["codex", "exec", "--sandbox", self.sandbox, "-C", str(cwd), "--skip-git-repo-check",
               "--output-last-message", last, "--color", "never"]
        if self.json_events:
            cmd.append("--json")
        if self.ephemeral:
            cmd.append("--ephemeral")
        for ov in self.overrides:
            cmd += ["-c", ov]
        if model:
            cmd += ["-m", model]
        cmd.append(prompt)
        tokens: dict = {}
        steps = [0]

        def rel(v: str) -> str:
            try:
                return str(Path(v).resolve().relative_to(Path(cwd).resolve()))
            except Exception:
                return str(v)

        def on_line(line: str):
            line = line.strip()
            if not line.startswith("{"):
                return
            d = json.loads(line)
            it = d.get("item") or {}
            t, kind = d.get("type", ""), it.get("type", "")
            if kind in ("command_execution", "file_change") and t.endswith("completed"):
                steps[0] += 1
            if on_activity:
                if kind == "command_execution" and t.endswith("started"):
                    c = str(it.get("command", ""))
                    c = re.sub(r"""^/bin/\w+ -lc (["'])(.*)\1$""", r"\2", c, flags=re.S)
                    on_activity("Bash", c[:120])
                elif kind == "file_change" and t.endswith("completed"):
                    on_activity("Edit", ", ".join(rel(str(c.get("path", ""))) for c in it.get("changes", []))[:120])
                elif kind == "agent_message" and t.endswith("completed") and it.get("text"):
                    on_activity("💬", str(it["text"]).replace("\n", " ")[:140])
            if t == "turn.completed" and isinstance(d.get("usage"), dict):
                for k, v in d["usage"].items():
                    if isinstance(v, (int, float)):
                        tokens[k] = tokens.get(k, 0) + v

        t0 = time.monotonic()
        try:
            r = _stream(cmd, None, timeout_s, on_line) if self.json_events else _run(cmd, None, timeout_s)
        except subprocess.TimeoutExpired:
            return WorkerResult(False, error=f"timeout after {timeout_s}s", seconds=time.monotonic() - t0)
        secs = time.monotonic() - t0
        if STOP.is_set():
            return WorkerResult(False, error="interrupted (orchestrator stopping)", seconds=secs)
        summary = ""
        try:
            summary = Path(last).read_text().strip()
        except Exception:
            pass
        finally:
            try:
                os.unlink(last)
            except OSError:
                pass
        # token usage, if codex reported it
        m = re.search(r"tokens used[:\s]+([\d,]+)", (r.stdout + r.stderr), re.I)
        raw = {"tokens": int(m.group(1).replace(",", ""))} if m else ({"usage": tokens} if tokens else {})
        total = (tokens.get("input_tokens", 0) + tokens.get("output_tokens", 0)) or None
        turns = steps[0] or None
        if r.returncode != 0:
            return WorkerResult(False, summary=summary[:2000], error=(r.stderr or r.stdout)[-800:], seconds=secs, raw=raw, tokens=total, turns=turns)
        return WorkerResult(True, summary=summary[:2000] or "(no final message)", seconds=secs, raw=raw, tokens=total, turns=turns)


# --------------------------------------------------------------------------
class ApiWorker:
    """Minimal tool loop on the Messages API — the harness-free worker."""
    name = "api"
    TOOLS = [
        {"name": "read_file", "description": "Read up to 400 lines of a file from start_line (1-indexed).",
         "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "start_line": {"type": "integer"}}, "required": ["path"]}},
        {"name": "grep", "description": "Regex search across the working copy (max 40 hits).",
         "input_schema": {"type": "object", "properties": {"pattern": {"type": "string"}}, "required": ["pattern"]}},
        {"name": "edit_file", "description": "Replace an exact unique snippet in a file.",
         "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "old_string": {"type": "string"}, "new_string": {"type": "string"}}, "required": ["path", "old_string", "new_string"]}},
        {"name": "write_file", "description": "Create or overwrite a file.",
         "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}},
        {"name": "run_check", "description": "Run the task's verification command and return its output.",
         "input_schema": {"type": "object", "properties": {}, "required": []}},
        {"name": "done", "description": "Call when the task is complete and the check passes.",
         "input_schema": {"type": "object", "properties": {"summary": {"type": "string"}}, "required": ["summary"]}},
    ]
    SYSTEM = ("You are an autonomous software engineering agent working alone in a repository. Be surgical: grep to "
              "locate, read only what you need, make minimal edits, run the check, then call done. Never modify tests.")
    PRICE = {"input": 1.0, "output": 5.0, "cache_read": 0.1, "cache_write": 1.25}   # Haiku 4.5 $/MTok

    def __init__(self, check_cmd: Optional[str] = None, protected: tuple = ("tests/",)):
        self.check_cmd = check_cmd
        self.protected = tuple(protected)          # path prefixes the worker may not write (tests, fixtures, the plan)

    def _protected(self, rel: str) -> bool:
        r = rel.lstrip("./")
        return any(r == p.rstrip("/") or r.startswith(p) for p in self.protected)

    def _safe(self, cwd: Path, rel: str) -> Path:
        p = (cwd / rel).resolve()
        if not str(p).startswith(str(cwd.resolve())):
            raise ValueError("path escapes working copy")
        return p

    def _dispatch(self, cwd: Path, name: str, a: dict) -> str:
        try:
            if name == "read_file":
                lines = self._safe(cwd, a["path"]).read_text().splitlines()
                s = max(1, int(a.get("start_line") or 1))
                chunk = lines[s - 1:s - 1 + 400]
                return f"[{a['path']}: {len(lines)} lines; showing {s}-{s + len(chunk) - 1}]\n" + "\n".join(f"{s + i:5d}\t{l}" for i, l in enumerate(chunk))
            if name == "grep":
                rx = re.compile(a["pattern"])
                hits = []
                for p in sorted(cwd.rglob("*")):
                    if p.suffix not in (".py", ".js", ".ts", ".md", ".toml", ".json", ".txt", ".yaml", ".yml") or ".mas" in p.parts or ".git" in p.parts:
                        continue
                    try:
                        for n, line in enumerate(p.read_text().splitlines(), 1):
                            if rx.search(line):
                                hits.append(f"{p.relative_to(cwd)}:{n}: {line.strip()[:160]}")
                                if len(hits) >= 40:
                                    return "\n".join(hits) + "\n[capped]"
                    except Exception:
                        continue
                return "\n".join(hits) or "no matches"
            if name == "edit_file":
                if self._protected(a["path"]):
                    return f"ERROR: {a['path']} is protected (tests/fixtures are the contract); write only your own file."
                p = self._safe(cwd, a["path"]); t = p.read_text()
                n = t.count(a["old_string"])
                if n != 1:
                    return f"ERROR: old_string found {n} times; must be exactly 1."
                p.write_text(t.replace(a["old_string"], a["new_string"], 1)); return f"edited {a['path']}"
            if name == "write_file":
                if self._protected(a["path"]):
                    return f"ERROR: {a['path']} is protected (tests/fixtures are the contract); write only your own file."
                p = self._safe(cwd, a["path"]); p.parent.mkdir(parents=True, exist_ok=True); p.write_text(a["content"]); return f"wrote {a['path']}"
            if name == "run_check":
                if not self.check_cmd:
                    return "no check configured"
                r = subprocess.run(self.check_cmd, shell=True, cwd=cwd, capture_output=True, text=True, timeout=180)
                out = (r.stdout + r.stderr).strip()
                return (out[:1200] + "\n...\n" + out[-1600:]) if len(out) > 3000 else (out or "(no output)")
        except Exception as e:
            return f"ERROR: {e}"
        return f"ERROR: unknown tool {name}"

    def run(self, prompt: str, cwd: Path, model: Optional[str], max_turns: int, timeout_s: int, on_activity=None) -> WorkerResult:
        import anthropic
        client = anthropic.Anthropic()
        model = model or "claude-haiku-4-5-20251001"
        messages = [{"role": "user", "content": [{"type": "text", "text": prompt}]}]
        usage = {"input": 0, "output": 0, "cache_read": 0, "cache_write": 0}
        t0 = time.monotonic(); turns = 0; summary = None
        while turns < max_turns and time.monotonic() - t0 < timeout_s and not STOP.is_set():
            for m in messages:
                if isinstance(m["content"], list):
                    for b in m["content"]:
                        if isinstance(b, dict):
                            b.pop("cache_control", None)
            tail = messages[-1]["content"]
            if isinstance(tail, list) and tail and isinstance(tail[-1], dict):
                tail[-1]["cache_control"] = {"type": "ephemeral"}
            delay = 2.0
            for attempt in range(6):
                try:
                    resp = client.messages.create(model=model, max_tokens=4000,
                                                  system=[{"type": "text", "text": self.SYSTEM, "cache_control": {"type": "ephemeral"}}],
                                                  tools=self.TOOLS, messages=messages)
                    break
                except (anthropic.RateLimitError, anthropic.InternalServerError, anthropic.APIConnectionError):
                    if attempt == 5:
                        raise
                    time.sleep(delay); delay = min(delay * 2, 60)
            turns += 1
            u = resp.usage
            usage["input"] += u.input_tokens; usage["output"] += u.output_tokens
            usage["cache_read"] += getattr(u, "cache_read_input_tokens", 0) or 0
            usage["cache_write"] += getattr(u, "cache_creation_input_tokens", 0) or 0
            calls = [b for b in resp.content if b.type == "tool_use"]
            if on_activity:
                for b in resp.content:
                    if b.type == "text" and b.text.strip():
                        on_activity("💬", b.text.strip().replace("\n", " ")[:140])
                for tu in calls:
                    on_activity(tu.name, summarize_tool(tu.name, tu.input or {}, cwd))
            if not calls:
                break
            messages.append({"role": "assistant", "content": resp.content})
            results, stop = [], False
            for tu in calls:
                a = tu.input or {}
                if tu.name == "done":
                    summary = a.get("summary", ""); out = "acknowledged"; stop = True
                else:
                    out = self._dispatch(cwd, tu.name, a)
                results.append({"type": "tool_result", "tool_use_id": tu.id, "content": out})
            messages.append({"role": "user", "content": results})
            if stop:
                break
        cost = sum(usage[k] / 1e6 * self.PRICE[k] for k in self.PRICE)
        return WorkerResult(ok=summary is not None, summary=summary or "(stopped without done)", turns=turns,
                            cost_usd=round(cost, 4), seconds=time.monotonic() - t0, tokens=sum(usage.values()) or None,
                            raw={"usage": usage, "model": model})


# --------------------------------------------------------------------------
class GeminiApiWorker(ApiWorker):
    """The API tool loop on Gemini (function calling). Same tools, same contract, cheap Flash models.
    Cost is estimated only for models with a known price; tokens are always reported."""
    name = "gemini"
    PRICES = {  # $ per 1M tokens (input, output) — public list prices; unknown models → cost None
        "gemini-2.5-flash": (0.30, 2.50), "gemini-2.5-flash-lite": (0.10, 0.40),
        "gemini-2.5-pro": (1.25, 10.0),
    }

    def _client(self):
        from google import genai
        return genai.Client()                      # reads GEMINI_API_KEY

    def _generate(self, client, model, contents, config):
        return client.models.generate_content(model=model, contents=contents, config=config)

    def run(self, prompt: str, cwd: Path, model: Optional[str], max_turns: int, timeout_s: int, on_activity=None) -> WorkerResult:
        from google.genai import types, errors
        model = model or "gemini-2.5-flash"
        client = self._client()
        decls = [types.FunctionDeclaration(name=t["name"], description=t["description"], parameters=t["input_schema"]) for t in self.TOOLS]
        config = types.GenerateContentConfig(
            tools=[types.Tool(function_declarations=decls)], system_instruction=self.SYSTEM, temperature=0.2,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True))
        contents = [types.Content(role="user", parts=[types.Part.from_text(text=prompt)])]
        usage = {"input": 0, "output": 0}
        t0 = time.monotonic(); turns = 0; summary = None; last_error = None
        while turns < max_turns and time.monotonic() - t0 < timeout_s and not STOP.is_set():
            delay = 2.0; resp = None
            for attempt in range(6):
                try:
                    resp = self._generate(client, model, contents, config)
                    break
                except errors.APIError as e:
                    code = getattr(e, "code", None)
                    if code in (429, 500, 502, 503, 504) and attempt < 5:
                        time.sleep(delay); delay = min(delay * 2, 60); continue
                    last_error = f"gemini {code}: {str(e)[:300]}"; break
            if resp is None:
                break
            turns += 1
            u = getattr(resp, "usage_metadata", None)
            if u:
                usage["input"] += u.prompt_token_count or 0
                usage["output"] += (u.candidates_token_count or 0) + (getattr(u, "thoughts_token_count", 0) or 0)
            cand = resp.candidates[0] if getattr(resp, "candidates", None) else None
            if not cand or not cand.content or not cand.content.parts:
                break
            contents.append(cand.content)
            calls = [p.function_call for p in cand.content.parts if getattr(p, "function_call", None)]
            if on_activity:
                for p in cand.content.parts:
                    if getattr(p, "text", None) and p.text.strip():
                        on_activity("💬", p.text.strip().replace("\n", " ")[:140])
            if not calls:
                break
            parts, stop = [], False
            for fc in calls:
                a = dict(fc.args or {})
                if on_activity:
                    on_activity(fc.name, summarize_tool(fc.name, a, cwd))
                if fc.name == "done":
                    summary = str(a.get("summary", "")); out = "acknowledged"; stop = True
                else:
                    out = self._dispatch(cwd, fc.name, a)
                parts.append(types.Part.from_function_response(name=fc.name, response={"result": out}))
            contents.append(types.Content(role="user", parts=parts))
            if stop:
                break
        price = self.PRICES.get(model)
        cost = round(usage["input"] / 1e6 * price[0] + usage["output"] / 1e6 * price[1], 4) if price else None
        return WorkerResult(ok=summary is not None, summary=summary or ("(stopped without done)" if not last_error else ""),
                            turns=turns, cost_usd=cost, error=last_error, seconds=time.monotonic() - t0,
                            tokens=(usage["input"] + usage["output"]) or None, raw={"usage": usage, "model": model})


# --------------------------------------------------------------------------
class ExecWorker:
    """Any harness with a headless mode, described in config — no code needed.

    "harnesses": {
      "aider": {
        "cmd": ["aider", "--yes-always", "--no-auto-commits", "--message", "{prompt}", "--model", "{model}"],
        "prompt_via": "arg",              # arg (a {prompt} placeholder) | stdin | file (a {prompt_file} placeholder)
        "summary": "stdout_tail",         # stdout_tail | file (an {out_file} placeholder the harness writes)
        "activity": "lines",              # none | lines (each stdout line) | json:<field>  (JSONL: show that field)
        "env": {"AIDER_NO_ANALYTICS": "1"},
        "cwd": true                       # run inside the compartment (default true); "{cwd}" is also available
      }
    }
    Placeholders: {prompt} {prompt_file} {cwd} {model} {max_turns} {out_file} {board} {root}. An argument that
    expands to an empty string (no model on this tier, say) is dropped, as is a "--flag" that
    immediately precedes it.
    """
    name = "exec"

    def __init__(self, kind: str, spec: dict, context: Optional[dict] = None):
        self.kind, self.spec = kind, spec
        self.name = kind
        self.context = context or {}          # {board}, {root} — for deterministic steps that read the board
        if not spec.get("cmd"):
            raise ValueError(f"harness {kind!r} needs a 'cmd' list in config")

    def _expand(self, tokens: list, vars_: dict) -> list:
        out = []
        for tok in tokens:
            try:
                val = str(tok).format(**vars_)
            except (KeyError, IndexError):
                val = str(tok)
            if val == "" and "{" in str(tok):
                if out and out[-1].startswith("-"):
                    out.pop()                       # drop the flag whose value is empty
                continue
            out.append(val)
        return out

    def run(self, prompt: str, cwd: Path, model: Optional[str], max_turns: int, timeout_s: int, on_activity=None) -> WorkerResult:
        spec = self.spec
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as pf:
            pf.write(prompt); prompt_file = pf.name
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as of:
            out_file = of.name
        vars_ = {"prompt": prompt, "prompt_file": prompt_file, "cwd": str(cwd), "model": model or "",
                 "max_turns": str(max_turns), "out_file": out_file, **{k: str(v) for k, v in self.context.items()}}
        cmd = self._expand(list(spec["cmd"]), vars_)
        env = {**os.environ, **{k: str(v).format(**vars_) for k, v in (spec.get("env") or {}).items()}}
        run_cwd = cwd if spec.get("cwd", True) else None
        stdin_text = prompt if spec.get("prompt_via") == "stdin" else None
        activity = spec.get("activity", "none")
        lines: list = []
        json_field = activity[5:] if activity.startswith("json:") else None
        last_emit = [0.0]

        def on_line(line: str):
            line = line.rstrip("\n")
            if not line.strip():
                return
            lines.append(line)
            if not on_activity or activity == "none":
                return
            if json_field:
                try:
                    d = json.loads(line)
                except Exception:
                    return
                val = d
                for part in json_field.split("."):
                    val = val.get(part) if isinstance(val, dict) else None
                if val:
                    on_activity(self.kind, str(val)[:140])
            elif time.monotonic() - last_emit[0] > 0.5:          # "lines": rate-limited so chatty tools don't flood the board
                last_emit[0] = time.monotonic()
                on_activity(self.kind, line.strip()[:140])

        t0 = time.monotonic()
        try:
            r = _stream(cmd, run_cwd, timeout_s, on_line, env=env, stdin_text=stdin_text)
        except FileNotFoundError:
            return WorkerResult(False, error=f"harness {self.kind!r}: command not found: {cmd[0]}", seconds=time.monotonic() - t0)
        except subprocess.TimeoutExpired:
            return WorkerResult(False, error=f"timeout after {timeout_s}s", seconds=time.monotonic() - t0)
        finally:
            for f in (prompt_file,):
                try: os.unlink(f)
                except OSError: pass
        secs = time.monotonic() - t0
        summary = ""
        if spec.get("summary") == "file":
            try: summary = Path(out_file).read_text().strip()
            except OSError: summary = ""
        else:
            summary = "\n".join(lines[-12:]).strip()
        try: os.unlink(out_file)
        except OSError: pass
        if STOP.is_set():
            return WorkerResult(False, error="interrupted (orchestrator stopping)", seconds=secs)
        if r.returncode != 0:
            return WorkerResult(False, summary=summary[:2000], error=(r.stderr or summary)[-800:], seconds=secs)
        return WorkerResult(True, summary=summary[:2000] or "(no output)", seconds=secs, turns=len(lines) or None)


# Presets for harnesses with a documented headless mode. Flags were taken from each CLI's
# --help on 2026-09-03; "verified" means an item went through the whole mas loop here.
HARNESS_PRESETS = {
    "hermes": {
        "cmd": ["hermes", "-z", "{prompt}", "-m", "{model}", "--usage-file", "{out_file}"],
        "prompt_via": "arg", "summary": "stdout_tail", "activity": "lines",
        "_about": "Hermes Agent one-shot mode (-z): approvals auto-bypassed, prints only the final answer; --usage-file reports cost/tokens",
    },
    "gemini": {
        "cmd": ["gemini", "-p", "{prompt}", "--approval-mode", "yolo", "-m", "{model}", "-o", "text"],
        "prompt_via": "arg", "summary": "stdout_tail", "activity": "lines",
        "_about": "Gemini CLI headless (-p) with auto-approved tools; needs GEMINI_API_KEY or a configured auth method",
    },
    "opencode": {
        "cmd": ["opencode", "run", "{prompt}", "--auto", "--pure", "-m", "{model}", "--dir", "{cwd}"],
        "prompt_via": "arg", "summary": "stdout_tail", "activity": "lines",
        "_about": "OpenCode `run` with auto-approved permissions; model as provider/model; needs a configured provider",
    },
    "aider": {
        "cmd": ["aider", "--yes-always", "--no-auto-commits", "--no-git", "--message", "{prompt}", "--model", "{model}"],
        "prompt_via": "arg", "summary": "stdout_tail", "activity": "lines",
        "_about": "aider one-shot (--message); git handling off because mas owns the worktree and the commit",
    },
}


# --------------------------------------------------------------------------
def make_worker(kind: str, config: dict, check_cmd: Optional[str] = None, context: Optional[dict] = None):
    if kind == "claude":
        return ClaudeCliWorker(config.get("claude_allowed_tools", "Read,Edit,MultiEdit,Write,Grep,Glob,Bash(python:*),Bash(python3:*),Bash(pytest:*),Bash(npm:*),Bash(node:*),Bash(git status:*),Bash(git diff:*)"),
                               bare=bool(config.get("claude_bare", False)), check_cmd=check_cmd)
    if kind == "codex":
        return CodexCliWorker(sandbox=config.get("codex_sandbox", "workspace-write"),
                              overrides=config.get("codex_overrides", []), json_events=bool(config.get("codex_json_events", True)),
                              ephemeral=bool(config.get("codex_ephemeral", True)))
    protected = tuple(config.get("protected_paths", ["tests/"]))
    if kind == "api":
        return ApiWorker(check_cmd=check_cmd, protected=protected)
    if kind == "gemini":
        return GeminiApiWorker(check_cmd=check_cmd, protected=protected)
    spec = (config.get("harnesses") or {}).get(kind)
    if spec:
        return ExecWorker(kind, spec, context=context)
    raise ValueError(f"unknown worker kind: {kind} (built-in: claude, codex, api, gemini; or define it under config 'harnesses')")
