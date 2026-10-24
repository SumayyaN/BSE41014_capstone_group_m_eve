"""Rebuild the live-scenario runner sheet from the Week 7 results CSV."""
import csv
from pathlib import Path

from openpyxl import Workbook

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "docs" / "evaluation" / "Group_M_Week7_Scenario_Results.csv"
OUT = ROOT / "docs" / "evaluation" / "week8_runner_input.xlsx"


def student_text(raw: str) -> str:
    lines = [line.strip() for line in (raw or "").splitlines() if line.strip()]
    lines = [line for line in lines if not line.startswith("[Setup:")]
    return " ".join(lines)


def main() -> None:
    with SRC.open(encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    live = [r for r in rows if str(r["run_mode"]).startswith("Live")]
    wb = Workbook()
    ws = wb.active
    ws.title = "Runner input"
    ws.append(["id", "scenario_type", "preconditions", "sidebar_agree_before_turn", "student_turns"])
    for rec in live:
        raw = rec["input"]
        pre = "SEED_A" if "SEED_A" in raw else "none"
        agree = 1 if "sidebar agreement" in raw else ""
        ws.append([rec["scenario_id"], rec["scenario_type"], pre, agree, student_text(raw)])
    wb.save(OUT)
    print(f"source rows {len(rows)}")
    print(f"live rows {len(live)}")
    print(f"scripted rows {len(rows) - len(live)}")
    print(OUT)


if __name__ == "__main__":
    main()
