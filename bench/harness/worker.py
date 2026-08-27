"""Minimal tool-loop agent over the Anthropic Messages API.

The SAME agent class is used for both benchmark conditions (single vs multi);
only the brief and the turn budget differ, so the comparison stays fair.
"""
import os
import time
from pathlib import Path

import anthropic

MODEL = "claude-haiku-4-5-20251001"
MAX_TOKENS = 4000
READ_CAP = 20_000       # max chars returned by read_file
TEST_OUT_CAP = 3000     # max chars of pytest output returned

SYSTEM = """You are an autonomous software engineering agent working alone in a Python repository.

Your job: fix implementation code so the tests pass. The test files define correct behavior and are the source of truth — you must NEVER modify anything under tests/. Fix only implementation files under src/.

Method: run the relevant tests first to see failures, read the implementation, fix it, and re-run the tests to verify. When everything you were asked to fix is verified passing, call the `done` tool with a short summary. Be efficient — do not re-read files you have already seen."""

TOOLS = [
    {
        "name": "read_file",
        "description": "Read a file from the repository. Path is relative to the repo root.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        },
    },
    {
        "name": "write_file",
        "description": "Overwrite a file in the repository with new content. Path is relative to the repo root. Modifying test files is forbidden.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
            "required": ["path", "content"],
        },
    },
    {
        "name": "run_tests",
        "description": "Run pytest. Pass a specific test path (e.g. 'tests/test_foo.py') or omit to run the whole suite.",
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


class Worker:
    def __init__(self, repo_dir, python_bin, label="worker"):
        self.repo = Path(repo_dir).resolve()
        self.python = python_bin
        self.label = label
        self.client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        self.usage = {"input": 0, "output": 0, "cache_read": 0, "cache_write": 0}

    # ---- tool implementations -------------------------------------------
    def _safe(self, rel):
        p = (self.repo / rel).resolve()
        if not str(p).startswith(str(self.repo)):
            raise ValueError("path escapes repository")
        return p

    def _read_file(self, path):
        try:
            text = self._safe(path).read_text()
        except Exception as e:
            return f"ERROR: {e}"
        return text[:READ_CAP]

    def _write_file(self, path, content):
        rel = os.path.normpath(path)
        if rel.startswith("tests") or "/tests/" in rel:
            return "ERROR: modifying test files is forbidden."
        try:
            p = self._safe(rel)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content)
        except Exception as e:
            return f"ERROR: {e}"
        return f"wrote {rel} ({len(content)} chars)"

    def _run_tests(self, path=None):
        import subprocess

        cmd = [self.python, "-m", "pytest", "-q", "--no-header"]
        if path:
            cmd.append(path)
        try:
            r = subprocess.run(
                cmd, cwd=self.repo, capture_output=True, text=True, timeout=90
            )
        except subprocess.TimeoutExpired:
            return "ERROR: pytest timed out after 90s"
        out = (r.stdout + r.stderr).strip()
        if len(out) > TEST_OUT_CAP:
            out = out[:1200] + "\n...[truncated]...\n" + out[-1600:]
        return out or "(no output)"

    # ---- API call with retry + prompt caching ---------------------------
    def _call(self, messages):
        # move the incremental cache breakpoint to the newest message
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
                    tools=TOOLS,
                    messages=messages,
                )
            except (anthropic.RateLimitError, anthropic.InternalServerError,
                    anthropic.APIConnectionError) as e:
                if attempt == 5:
                    raise
                print(f"[{self.label}] retry after {type(e).__name__} ({delay:.0f}s)")
                time.sleep(delay)
                delay = min(delay * 2, 60)

    # ---- main loop -------------------------------------------------------
    def run(self, brief, max_turns):
        messages = [{"role": "user", "content": [{"type": "text", "text": brief}]}]
        t0 = time.monotonic()
        done_summary = None
        turns = 0
        while turns < max_turns:
            resp = self._call(messages)
            turns += 1
            u = resp.usage
            self.usage["input"] += u.input_tokens
            self.usage["output"] += u.output_tokens
            self.usage["cache_read"] += getattr(u, "cache_read_input_tokens", 0) or 0
            self.usage["cache_write"] += getattr(u, "cache_creation_input_tokens", 0) or 0

            tool_uses = [b for b in resp.content if b.type == "tool_use"]
            if not tool_uses:
                break  # agent stopped talking without calling done
            messages.append({"role": "assistant", "content": resp.content})

            results = []
            stop = False
            for tu in tool_uses:
                args = tu.input or {}
                if tu.name == "read_file":
                    out = self._read_file(args.get("path", ""))
                elif tu.name == "write_file":
                    out = self._write_file(args.get("path", ""), args.get("content", ""))
                elif tu.name == "run_tests":
                    out = self._run_tests(args.get("path"))
                elif tu.name == "done":
                    done_summary = args.get("summary", "")
                    out = "acknowledged"
                    stop = True
                else:
                    out = f"ERROR: unknown tool {tu.name}"
                results.append({"type": "tool_result", "tool_use_id": tu.id,
                                "content": out})
            messages.append({"role": "user", "content": results})
            if stop:
                break

        return {
            "label": self.label,
            "turns": turns,
            "seconds": round(time.monotonic() - t0, 1),
            "done_summary": done_summary,
            "usage": dict(self.usage),
        }
