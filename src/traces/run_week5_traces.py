"""Run the three Week 5 execution traces and save them under evidence/traces/.

T1 is a grounded answer. T2 is a draft created after the agreement control.
T3 is a rejected registration number, then one corrected attempt.

The agreement flag is set the same way the sidebar button sets it. Drafts
from these runs go to a temporary file, not data/cases/drafts.json.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from agent.state import SessionState
from tools import case_store
from tools.orchestrate import run_tool_turn

OUT_DIR = ROOT / "evidence" / "traces"
DRAFT_STORE = ROOT / "evidence" / "traces" / "_drafts_during_run.json"


def _short_result(result: dict) -> dict:
    status = result.get("status")
    brief = {"status": status}
    if result.get("message"):
        brief["message"] = result["message"]
    if result.get("validation_errors"):
        brief["validation_errors"] = result["validation_errors"]
    if result.get("retrieved_count") is not None:
        brief["retrieved_count"] = result["retrieved_count"]
    if status == "ok":
        brief["sources"] = [
            {
                "source_title": chunk.get("source_title"),
                "source_url": chunk.get("source_url"),
                "similarity_score": chunk.get("similarity_score"),
            }
            for chunk in result.get("chunks") or []
        ]
    for key in ("case_id", "session_id", "routed_queue", "created_at"):
        if key in result:
            brief[key] = result[key]
    return brief


def _turn(state: SessionState, message: str, events: list[str] | None = None) -> dict:
    result = run_tool_turn(state, message)
    return {
        "application_events": events or [],
        "student_message": message,
        "reply": result["text"],
        "stop_condition": result.get("stop_condition"),
        "iteration_count": result.get("iteration_count"),
        "tools": [
            {
                "tool": step["tool"],
                "arguments": step["arguments"],
                "result": _short_result(step["result"]),
            }
            for step in result.get("trace") or []
        ],
    }


def _save(name: str, document: dict) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / name
    path.write_text(json.dumps(document, indent=2), encoding="utf-8")
    print(f"wrote {path}")


def trace_t1() -> None:
    case_store.STORE_PATH = DRAFT_STORE
    state = SessionState()
    turn = _turn(state, "How do I activate my Makerere webmail account?")
    _save("T1_grounded_answer.json", {
        "id": "T1",
        "scenario": "Grounded answer from the approved documents, then stop.",
        "session_id": state.session_id,
        "turns": [turn],
    })


def trace_t2() -> None:
    case_store.STORE_PATH = DRAFT_STORE
    if DRAFT_STORE.exists():
        DRAFT_STORE.unlink()
    state = SessionState()
    first = _turn(state, "What was the score of the last Makerere basketball match?")
    state.case_agreed = True
    second = _turn(
        state,
        "My registration number is 23/U/22615. Wi-Fi in the hostel will not connect. "
        "Please create a support draft in category it_webmail_wifi.",
        ["Student used the agreement control. case_agreed is now true."],
    )
    _save("T2_case_draft.json", {
        "id": "T2",
        "scenario": "No matching document, then the student agrees, then a draft is saved.",
        "session_id": state.session_id,
        "turns": [first, second],
    })


def trace_t3() -> None:
    case_store.STORE_PATH = DRAFT_STORE
    if DRAFT_STORE.exists():
        DRAFT_STORE.unlink()
    state = SessionState()
    state.case_agreed = True
    first = _turn(
        state,
        "My registration number is 23/A/93939. Wi-Fi will not connect. "
        "Please create a support draft in category it_webmail_wifi.",
        ["Student had already used the agreement control."],
    )
    created = any(
        step["result"].get("status") == "created"
        for step in first["tools"]
        if step["tool"] == "create_support_case"
    )
    turns = [first]
    if first["tools"] and not created and not state.draft_already_created():
        turns.append(_turn(
            state,
            "The correct registration number is 23/U/22615. "
            "Please create the support draft with that number.",
        ))
    _save("T3_failure_recovery.json", {
        "id": "T3",
        "scenario": "A registration number is rejected, then one corrected attempt is made.",
        "session_id": state.session_id,
        "turns": turns,
    })


def main() -> None:
    chosen = sys.argv[1:] or ["T1", "T2", "T3"]
    runners = {"T1": trace_t1, "T2": trace_t2, "T3": trace_t3}
    for name in chosen:
        runners[name]()
    if DRAFT_STORE.exists():
        DRAFT_STORE.unlink()


if __name__ == "__main__":
    main()
