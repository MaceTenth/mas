#!/usr/bin/env python3
"""Independent deterministic gates for Demo 6's deliberately unreliable workers."""
from __future__ import annotations

import json
import sys
from pathlib import Path


EXPECTED = {
    "crash-resume": ("artifacts/crash.txt", "recovered-after-dead-lease"),
    "heartbeat-survival": ("artifacts/heartbeat.txt", "heartbeat-kept-lease"),
    "gate-retry": ("artifacts/gate-retry.txt", "repaired-by-retry"),
    "worker-crash": ("artifacts/worker-crash.txt", "recovered-after-process-exit"),
    "timeout-recovery": ("artifacts/timeout.txt", "recovered-after-timeout"),
    "idempotent": ("artifacts/idempotent.txt", "canonical-result"),
    "scoped-merge": ("artifacts/scoped.txt", "allowed-result"),
    "lesson-source": ("artifacts/lesson-source.txt", "lesson-published"),
    "lesson-consumer": ("artifacts/lesson-consumer.txt", "learned-cobalt-42"),
    # No worker ever writes this value: both attempts must be rejected.
    "permanent-failure": ("artifacts/permanent.txt", "impossible-recovery"),
}


def main(root: Path, case: str) -> int:
    if case == "final":
        try:
            report = json.loads((root / "result" / "recovery.json").read_text())
            markdown = (root / "result" / "recovery.md").read_text()
        except Exception as exc:
            print(f"recovery report missing or invalid: {exc}")
            return 1
        failed = [row for row in report.get("checks", []) if not row.get("passed")]
        expected_total = 18
        if report.get("total") != expected_total or report.get("passed") != expected_total or failed or "Board observed" not in markdown:
            print(f"recovery evidence incomplete: {report.get('passed')}/{report.get('total')}; failed={failed}")
            return 1
        print(f"recovery evidence: {report['passed']}/{report['total']} patterns demonstrated")
        return 0

    rel, expected = EXPECTED.get(case, (None, None))
    if not rel:
        print(f"unknown verification case: {case}")
        return 2
    path = root / rel
    actual = path.read_text().strip() if path.exists() else "[missing]"
    if actual != expected:
        print(f"{case}: expected {expected!r}, got {actual!r}")
        return 1
    print(f"{case}: verified {rel}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: verify.py <root> <case>")
    raise SystemExit(main(Path(sys.argv[1]), sys.argv[2]))
