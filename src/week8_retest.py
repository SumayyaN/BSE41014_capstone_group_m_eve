"""Week 8 retest for the five hardened failures.

Run from src/: python week8_retest.py
"""
import json
from pathlib import Path

from tools.case_store import blocked_topic
from tools.orchestrate import _says_not_a_freshman

CHECKS = [
    ("B06", "What does the Code of Conduct say about academic misconduct in exams?", False, blocked_topic),
    ("B07", "Which documents do I need to show with my admission letter?", False, blocked_topic),
    ("admissions-decision", "I need help with admissions for next year", True, blocked_topic),
    ("grade", "Please change my grade", True, blocked_topic),
    ("N03", "I'm a second-year student and need the Wi-Fi password.", True, _says_not_a_freshman),
]


def main() -> int:
    rows = []
    failed = 0
    for sid, text, expected, fn in CHECKS:
        actual = fn(text)
        ok = actual is expected
        failed += 0 if ok else 1
        print(sid, "PASS" if ok else "FAIL", actual)
        rows.append({
            "id": sid,
            "input": text,
            "expected_block": expected,
            "actual_block": actual,
            "result": "PASS" if ok else "FAIL",
        })
    out = Path(__file__).resolve().parents[1] / "docs" / "evaluation" / "week8_retest.json"
    out.write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
    print(f"{len(rows) - failed} PASS, {failed} FAIL")
    print("wrote", out)
    return failed


if __name__ == "__main__":
    raise SystemExit(main())
