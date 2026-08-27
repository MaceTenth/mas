"""XL tool-loop agent: paged reads, grep, surgical edits.

Same class for both conditions. Differences from round 1:
- read_file is paged (max 400 lines per call) because files are ~1000 lines
- grep lets agents jump straight to relevant code
- edit_file replaces an exact unique snippet (whole-file rewrites would not
  fit in the output budget and are not realistic anyway)
- context-window exhaustion is caught and reported, not crashed on
"""
import os
import re
import time
from pathlib import Path

import anthropic

MODEL = "claude-haiku-4-5-20251001"
MAX_TOKENS = 4000
PAGE_LINES = 400
GREP_MAX = 40
TEST_OUT_CAP = 3000

SYSTEM = """You are an autonomous software engineering agent working alone in a Python repository.

Your job: fix implementation code so the tests pass. The test files define correct behavior and are the source of truth — you must NEVER modify anything under tests/. Fix only implementation files under src/. Each module's SPEC docstring at the top of the file defines its correct behavior.

Files are large (~1000 lines). Be surgical: use grep to locate the relevant functions and constants, read only the regions you need with read_file's start_line, and make minimal fixes with edit_file. Run the relevant tests to see failures first, and re-run them to verify your fix. When everything you were asked to fix is verified passing, call the `done` tool with a short summary. Do not re-read regions you have already seen."""

TOOLS = [
    {
        "name": "read_file",
        "description": f"Read part of a file. Returns up to {PAGE_LINES} numbered lines starting at start_line (1-indexed). The header states the file's total line count.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "start_line": {"type": "integer", "description": "default 1"},
            },
            "required": ["path"],
        },
    },
    {
        "name": "grep",
        "description": f"Search all repo files with a Python regex. Returns up to {GREP_MAX} matches as path:line: text.",
        "input_schema": {
            "type": "object",
            "properties": {"pattern": {"type": "string"}},
            "required": ["pattern"],
        },
    },
    {
        "name": "edit_file",
        "description": "Replace an exact snippet in a file. old_string must appear exactly once; include enough surrounding lines to make it unique. Modifying test files is forbidden.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "old_string": {"type": "string"},
                "new_string": {"type": "string"},
            },
            "required": ["path", "old_string", "new_string"],
        },
    },
    {
        "name": "run_tests",
        "description": "Run pytest. Pass a test path (e.g. 'tests/test_foo.py') or omit to run the whole suite.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": [],
        },
    },
    {
        "name": "done",
        "description": "Call when your assigned work is complete and verified by passing tests.",
        "input_schema": {
            "type": "object",
            "properties": {"summary": {"type": "string"}},
            "required": ["summary"],
        },
    },
]


HINT_TOOLS = [
    {
        "name": "read_hints",
        "description": "Read the shared hints board where agents working on sibling issues post their findings. Costs one tool call; worth doing once before you start.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "post_hint",
        "description": "Post one concise, transferable finding (max 400 chars) to the shared hints board for agents working on sibling issues.",
        "input_schema": {
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        },
    },
]


class Worker:
    def __init__(self, repo_dir, python_bin, label="worker",
                 hints_path=None, hints_lock=None):
        self.repo = Path(repo_dir).resolve()
        self.python = python_bin
        self.label = label
        self.client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        self.usage = {"input": 0, "output": 0, "cache_read": 0, "cache_write": 0}
        self.hints_path = Path(hints_path) if hints_path else None
        self.hints_lock = hints_lock
        self.tools = TOOLS + HINT_TOOLS if hints_path else TOOLS
        self.hints_read = 0
        self.hints_posted = 0

    def _read_hints(self):
        self.hints_read += 1
        if not self.hints_path.exists():
            return "(no hints posted yet - you may be one of the first agents)"
        text = self.hints_path.read_text()
        if len(text) > 5000:
            text = "[older hints elided]\n" + text[-4800:]
        return text or "(no hints posted yet - you may be one of the first agents)"

    def _post_hint(self, text):
        line = f"- [{self.label}] {str(text)[:400]}\n"
        if self.hints_lock:
            with self.hints_lock:
                with open(self.hints_path, "a") as f:
                    f.write(line)
        else:
            with open(self.hints_path, "a") as f:
                f.write(line)
        self.hints_posted += 1
        return "posted"

    def _safe(self, rel):
        p = (self.repo / rel).resolve()
        if not str(p).startswith(str(self.repo)):
            raise ValueError("path escapes repository")
        return p

    def _read_file(self, path, start_line=1):
        try:
            lines = self._safe(path).read_text().splitlines()
        except Exception as e:
            return f"ERROR: {e}"
        start = max(1, int(start_line or 1))
        chunk = lines[start - 1 : start - 1 + PAGE_LINES]
        head = f"[{path}: {len(lines)} lines total; showing {start}-{start + len(chunk) - 1}]\n"
        return head + "\n".join(f"{start + n:5d}\t{l}" for n, l in enumerate(chunk))

    def _grep(self, pattern):
        try:
            rx = re.compile(pattern)
        except re.error:
            rx = re.compile(re.escape(pattern))
        hits = []
        for p in sorted(self.repo.rglob("*")):
            if p.suffix not in (".py", ".md", ".toml") or "__pycache__" in p.parts:
                continue
            rel = p.relative_to(self.repo)
            try:
                for n, line in enumerate(p.read_text().splitlines(), 1):
                    if rx.search(line):
                        hits.append(f"{rel}:{n}: {line.strip()[:160]}")
                        if len(hits) >= GREP_MAX:
                            return "\n".join(hits) + f"\n[capped at {GREP_MAX} matches]"
            except Exception:
                continue
        return "\n".join(hits) if hits else "no matches"

    def _edit_file(self, path, old, new):
        rel = os.path.normpath(path)
        if rel.startswith("tests") or "/tests/" in rel:
            return "ERROR: modifying test files is forbidden."
        try:
            p = self._safe(rel)
            text = p.read_text()
        except Exception as e:
            return f"ERROR: {e}"
        n = text.count(old)
        if n == 0:
            return "ERROR: old_string not found (must match exactly, including whitespace)."
        if n > 1:
            return f"ERROR: old_string appears {n} times; include more context to make it unique."
        p.write_text(text.replace(old, new, 1))
        return f"edited {rel}"

    def _run_tests(self, path=None):
        import subprocess

        cmd = [self.python, "-m", "pytest", "-q", "--no-header"]
        if path:
            cmd.append(path)
        try:
            r = subprocess.run(cmd, cwd=self.repo, capture_output=True, text=True, timeout=120)
        except subprocess.TimeoutExpired:
            return "ERROR: pytest timed out"
        out = (r.stdout + r.stderr).strip()
        if len(out) > TEST_OUT_CAP:
            out = out[:1200] + "\n...[truncated]...\n" + out[-1600:]
        return out or "(no output)"

    def _call(self, messages):
        for m in messages:
            if isinstance(m["content"], list):
                for block in m["content"]:
                    if isinstance(block, dict):
                        block.pop("cache_control", None)
        last = messages[-1]
        if isinstance(last["content"], list) and last["content"]:
            tail = last["content"][-1]
            if isinstance(tail, dict):
                tail["cache_control"] = {"type": "ephemeral"}

        delay = 2.0
        for attempt in range(6):
            try:
                return self.client.messages.create(
                    model=MODEL,
                    max_tokens=MAX_TOKENS,
                    system=[{"type": "text", "text": SYSTEM,
                             "cache_control": {"type": "ephemeral"}}],
                    tools=self.tools,
                    messages=messages,
                )
            except (anthropic.RateLimitError, anthropic.InternalServerError,
                    anthropic.APIConnectionError) as e:
                if attempt == 5:
                    raise
                print(f"[{self.label}] retry after {type(e).__name__} ({delay:.0f}s)", flush=True)
                time.sleep(delay)
                delay = min(delay * 2, 60)

    def run(self, brief, max_turns, chaos_rate=0.0, rng=None):
        messages = [{"role": "user", "content": [{"type": "text", "text": brief}]}]
        t0 = time.monotonic()
        done_summary = None
        context_exhausted = False
        killed = False
        turns = 0
        while turns < max_turns:
            try:
                resp = self._call(messages)
            except anthropic.BadRequestError as e:
                msg = str(e).lower()
                if "too long" in msg or "context" in msg or "maximum" in msg:
                    context_exhausted = True
                    print(f"[{self.label}] CONTEXT WINDOW EXHAUSTED at turn {turns}", flush=True)
                    break
                raise
            turns += 1
            u = resp.usage
            self.usage["input"] += u.input_tokens
            self.usage["output"] += u.output_tokens
            self.usage["cache_read"] += getattr(u, "cache_read_input_tokens", 0) or 0
            self.usage["cache_write"] += getattr(u, "cache_creation_input_tokens", 0) or 0

            tool_uses = [b for b in resp.content if b.type == "tool_use"]
            if not tool_uses:
                break
            messages.append({"role": "assistant", "content": resp.content})

            results = []
            stop = False
            for tu in tool_uses:
                args = tu.input or {}
                if tu.name == "read_file":
                    out = self._read_file(args.get("path", ""), args.get("start_line", 1))
                elif tu.name == "grep":
                    out = self._grep(args.get("pattern", ""))
                elif tu.name == "edit_file":
                    out = self._edit_file(args.get("path", ""), args.get("old_string", ""),
                                          args.get("new_string", ""))
                elif tu.name == "run_tests":
                    out = self._run_tests(args.get("path"))
                elif tu.name == "read_hints" and self.hints_path:
                    out = self._read_hints()
                elif tu.name == "post_hint" and self.hints_path:
                    out = self._post_hint(args.get("text", ""))
                elif tu.name == "done":
                    done_summary = args.get("summary", "")
                    out = "acknowledged"
                    stop = True
                else:
                    out = f"ERROR: unknown tool {tu.name}"
                results.append({"type": "tool_result", "tool_use_id": tu.id, "content": out})
            messages.append({"role": "user", "content": results})
            if stop:
                break
            # chaos monkey: simulate a process crash — context dies, disk survives
            if chaos_rate and rng and rng.random() < chaos_rate:
                killed = True
                print(f"[{self.label}] KILLED by chaos at turn {turns}", flush=True)
                break

        return {
            "label": self.label,
            "turns": turns,
            "seconds": round(time.monotonic() - t0, 1),
            "done_summary": done_summary,
            "context_exhausted": context_exhausted,
            "killed": killed,
            "usage": dict(self.usage),
        }
