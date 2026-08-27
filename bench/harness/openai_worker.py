"""Small, auditable Responses API tool loop used by the swarm evaluation.

The benchmark deliberately uses the same loop, model, prompt, and tools for
single-agent and swarm conditions.  Only task partitioning and concurrency
change.  It is a benchmark harness, not a production sandbox.
"""

from __future__ import annotations

import json
import os
import random
import re
import subprocess
import time
from pathlib import Path
from typing import Any, Callable

import openai
from openai import OpenAI


MODEL = os.environ.get("SWARM_EVAL_MODEL", "gpt-5.6-luna")
MODEL_PRICE_PER_MTOK = {
    "input": 0.20,
    "cached_input": 0.02,
    "output": 1.20,
}


def function_tool(name: str, description: str, parameters: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "function",
        "name": name,
        "description": description,
        "parameters": parameters,
    }


def zero_usage() -> dict[str, int]:
    return {"input": 0, "cached_input": 0, "output": 0}


def merge_usage(target: dict[str, int], source: dict[str, int]) -> None:
    for key in target:
        target[key] += int(source.get(key, 0))


def estimated_cost(usage: dict[str, int]) -> float:
    uncached = max(0, usage["input"] - usage["cached_input"])
    value = (
        uncached * MODEL_PRICE_PER_MTOK["input"]
        + usage["cached_input"] * MODEL_PRICE_PER_MTOK["cached_input"]
        + usage["output"] * MODEL_PRICE_PER_MTOK["output"]
    ) / 1_000_000
    return round(value, 6)


class OpenAIToolAgent:
    """Run a Responses API agent until it stops, calls ``done``, or hits a cap."""

    def __init__(
        self,
        *,
        instructions: str,
        tools: list[dict[str, Any]],
        handlers: dict[str, Callable[[dict[str, Any]], str]],
        label: str,
        terminal_tools: tuple[str, ...] = ("done",),
        max_output_tokens: int = 3000,
        reasoning_effort: str = "low",
    ) -> None:
        self.instructions = instructions
        self.tools = tools
        self.handlers = handlers
        self.label = label
        self.terminal_tools = set(terminal_tools)
        self.max_output_tokens = max_output_tokens
        self.reasoning_effort = reasoning_effort
        self.client = OpenAI(max_retries=3, timeout=180.0)
        self.usage = zero_usage()

    def _record_usage(self, response: Any) -> None:
        usage = response.usage
        if usage is None:
            return
        cached = 0
        details = getattr(usage, "input_tokens_details", None)
        if details is not None:
            cached = int(getattr(details, "cached_tokens", 0) or 0)
        self.usage["input"] += int(getattr(usage, "input_tokens", 0) or 0)
        self.usage["cached_input"] += cached
        self.usage["output"] += int(getattr(usage, "output_tokens", 0) or 0)

    def _create(self, *, input_value: Any, previous_response_id: str | None) -> Any:
        delay = 2.0
        for attempt in range(6):
            try:
                return self.client.responses.create(
                    model=MODEL,
                    instructions=self.instructions,
                    input=input_value,
                    previous_response_id=previous_response_id,
                    tools=self.tools,
                    max_output_tokens=self.max_output_tokens,
                    reasoning={"effort": self.reasoning_effort},
                    parallel_tool_calls=True,
                )
            except (openai.RateLimitError, openai.APIConnectionError, openai.InternalServerError):
                if attempt == 5:
                    raise
                time.sleep(delay + random.random())
                delay = min(delay * 2, 30)

    def run(self, brief: str, max_turns: int) -> dict[str, Any]:
        started = time.monotonic()
        previous_response_id: str | None = None
        next_input: Any = brief
        turns = 0
        stopped_by: str | None = None
        final_text = ""
        context_exhausted = False
        error: str | None = None

        while turns < max_turns:
            try:
                response = self._create(
                    input_value=next_input,
                    previous_response_id=previous_response_id,
                )
            except openai.BadRequestError as exc:
                message = str(exc).lower()
                if "context" in message or "maximum" in message or "too many tokens" in message:
                    context_exhausted = True
                    error = str(exc)[:500]
                    break
                raise

            turns += 1
            self._record_usage(response)
            previous_response_id = response.id
            final_text = getattr(response, "output_text", "") or final_text
            calls = [item for item in response.output if item.type == "function_call"]
            if not calls:
                break

            outputs: list[dict[str, str]] = []
            stop = False
            for call in calls:
                try:
                    args = json.loads(call.arguments or "{}")
                except json.JSONDecodeError as exc:
                    result = f"ERROR: invalid JSON arguments: {exc}"
                else:
                    handler = self.handlers.get(call.name)
                    if handler is None:
                        result = f"ERROR: unknown tool {call.name}"
                    else:
                        try:
                            result = str(handler(args))
                        except Exception as exc:  # tool failures should be visible to the model
                            result = f"ERROR: {type(exc).__name__}: {exc}"
                outputs.append(
                    {
                        "type": "function_call_output",
                        "call_id": call.call_id,
                        "output": result,
                    }
                )
                if call.name in self.terminal_tools:
                    stopped_by = call.name
                    stop = True
            if stop:
                break
            next_input = outputs

        return {
            "label": self.label,
            "model": MODEL,
            "turns": turns,
            "wall_seconds": round(time.monotonic() - started, 3),
            "stopped_by": stopped_by,
            "context_exhausted": context_exhausted,
            "error": error,
            "final_text": final_text[:1000],
            "usage": dict(self.usage),
            "est_cost_usd": estimated_cost(self.usage),
        }


CODING_SYSTEM = """You are an autonomous software-engineering agent in a Python repository.

Fix only the requested implementation modules under src/. Tests are the source of truth and must never be changed. Run the relevant tests first, inspect the implementation, make minimal exact edits, then rerun tests. Call done only after your assigned tests pass. Be concise and avoid rereading regions already shown."""


CODING_TOOLS = [
    function_tool(
        "read_file",
        "Read up to 300 numbered lines from a repository file.",
        {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "start_line": {"type": "integer"},
            },
            "required": ["path"],
        },
    ),
    function_tool(
        "grep",
        "Search Python files with a regular expression and return matching lines.",
        {
            "type": "object",
            "properties": {"pattern": {"type": "string"}},
            "required": ["pattern"],
        },
    ),
    function_tool(
        "edit_file",
        "Replace one exact unique snippet in a Python file under src/.",
        {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "old_string": {"type": "string"},
                "new_string": {"type": "string"},
            },
            "required": ["path", "old_string", "new_string"],
        },
    ),
    function_tool(
        "run_tests",
        "Run pytest for one tests/test_NAME.py file, or the full suite when path is omitted.",
        {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": [],
        },
    ),
    function_tool(
        "done",
        "Finish after the assigned tests have passed.",
        {
            "type": "object",
            "properties": {"summary": {"type": "string"}},
            "required": [],
        },
    ),
]


class CodingTools:
    def __init__(self, repo_dir: Path, python_bin: str) -> None:
        self.repo = repo_dir.resolve()
        self.python = python_bin

    def _safe(self, rel: str) -> Path:
        candidate = (self.repo / rel).resolve()
        if not candidate.is_relative_to(self.repo):
            raise ValueError("path escapes repository")
        return candidate

    def read_file(self, args: dict[str, Any]) -> str:
        path = str(args.get("path", ""))
        start = max(1, int(args.get("start_line", 1) or 1))
        try:
            lines = self._safe(path).read_text().splitlines()
        except Exception as exc:
            return f"ERROR: {exc}"
        chunk = lines[start - 1 : start - 1 + 300]
        header = f"[{path}: {len(lines)} lines; showing {start}-{start + len(chunk) - 1}]"
        return header + "\n" + "\n".join(
            f"{start + index:5d}\t{line}" for index, line in enumerate(chunk)
        )

    def grep(self, args: dict[str, Any]) -> str:
        pattern = str(args.get("pattern", ""))
        try:
            regex = re.compile(pattern)
        except re.error:
            regex = re.compile(re.escape(pattern))
        hits: list[str] = []
        for path in sorted(self.repo.rglob("*.py")):
            if "__pycache__" in path.parts:
                continue
            for number, line in enumerate(path.read_text().splitlines(), 1):
                if regex.search(line):
                    hits.append(f"{path.relative_to(self.repo)}:{number}: {line[:180]}")
                    if len(hits) == 60:
                        return "\n".join(hits) + "\n[capped at 60 matches]"
        return "\n".join(hits) if hits else "no matches"

    def edit_file(self, args: dict[str, Any]) -> str:
        rel = str(args.get("path", ""))
        parts = Path(rel).parts
        if not parts or parts[0] != "src" or Path(rel).suffix != ".py":
            return "ERROR: edits are restricted to Python files under src/."
        old = str(args.get("old_string", ""))
        new = str(args.get("new_string", ""))
        try:
            path = self._safe(rel)
            text = path.read_text()
        except Exception as exc:
            return f"ERROR: {exc}"
        count = text.count(old)
        if count == 0:
            return "ERROR: old_string was not found exactly."
        if count > 1:
            return f"ERROR: old_string appears {count} times; include more context."
        path.write_text(text.replace(old, new, 1))
        return f"edited {rel}"

    def run_tests(self, args: dict[str, Any]) -> str:
        requested = args.get("path")
        if requested:
            requested = str(requested)
            if not re.fullmatch(r"tests/test_[A-Za-z0-9_]+\.py", requested):
                return "ERROR: path must be one tests/test_NAME.py file."
        command = [self.python, "-m", "pytest", "-q", "--no-header"]
        if requested:
            command.append(requested)
        clean_env = {
            key: value
            for key, value in os.environ.items()
            if key not in {"OPENAI_API_KEY", "ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN"}
        }
        try:
            result = subprocess.run(
                command,
                cwd=self.repo,
                env=clean_env,
                capture_output=True,
                text=True,
                timeout=120,
            )
        except subprocess.TimeoutExpired:
            return "ERROR: pytest timed out after 120 seconds"
        output = (result.stdout + result.stderr).strip()
        if len(output) > 5000:
            output = output[:2200] + "\n...[truncated]...\n" + output[-2200:]
        return f"exit_code={result.returncode}\n{output or '(no output)'}"

    @staticmethod
    def done(args: dict[str, Any]) -> str:
        return "acknowledged"

    def handlers(self) -> dict[str, Callable[[dict[str, Any]], str]]:
        return {
            "read_file": self.read_file,
            "grep": self.grep,
            "edit_file": self.edit_file,
            "run_tests": self.run_tests,
            "done": self.done,
        }


def coding_agent(repo_dir: Path, python_bin: str, label: str) -> OpenAIToolAgent:
    tools = CodingTools(repo_dir, python_bin)
    return OpenAIToolAgent(
        instructions=CODING_SYSTEM,
        tools=CODING_TOOLS,
        handlers=tools.handlers(),
        label=label,
    )
