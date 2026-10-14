"""Write one JSON turn log under logs/ for Week 7 observability evidence.

Each record matches the Step 1 field list: identity, model, prompt,
retrieval, tools, latency/errors, and outcome. Full prompt text and
passage bodies are not stored.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from agent.state import SessionState

ROOT = Path(__file__).resolve().parents[2]
LOG_DIR = ROOT / "logs"
MODEL_NAME = "gemini-3.6-flash"
PROMPT_ID = "v1.3"
REPLY_CHARS = 400


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


def _tool_steps(trace: list[dict]) -> list[dict]:
    steps = []
    for step in trace or []:
        result = step.get("result") or {}
        entry = {
            "tool": step.get("tool"),
            "arguments": step.get("arguments") or {},
            "result": _short_result(result),
        }
        steps.append(entry)
    return steps


def _retrieval(trace: list[dict]) -> list[dict]:
    rows = []
    for step in _tool_steps(trace):
        if step["tool"] != "retrieve_documents":
            continue
        result = step["result"]
        rows.append({
            "query": (step["arguments"] or {}).get("query"),
            "status": result.get("status"),
            "retrieved_count": result.get("retrieved_count"),
            "sources": result.get("sources") or [],
        })
    return rows


def _reply_preview(text: str | None) -> str:
    reply = text or ""
    if len(reply) <= REPLY_CHARS:
        return reply
    return reply[:REPLY_CHARS] + "..."


def write_turn_log(
    state: SessionState,
    *,
    student_message: str,
    reply: str,
    stop_condition: str | None,
    trace: list[dict],
    started_at: datetime,
    case_history_note: bool = False,
    error: str | None = None,
) -> Path | None:
    """Append one turn record under logs/. Returns the path, or None on write failure."""
    ended = datetime.now(timezone.utc)
    latency_ms = int((ended - started_at).total_seconds() * 1000)
    turn_id = str(uuid.uuid4())
    record = {
        "turn_id": turn_id,
        "session_id": state.session_id,
        "started_at": started_at.isoformat(),
        "ended_at": ended.isoformat(),
        "latency_ms": latency_ms,
        "model": {
            "name": MODEL_NAME,
            "rounds": state.iteration_count,
        },
        "prompt": {
            "id": PROMPT_ID,
            "case_history_note": bool(case_history_note),
        },
        "student_message": student_message,
        "retrieval": _retrieval(trace),
        "tools": _tool_steps(trace),
        "error": error,
        "outcome": {
            "stop_condition": stop_condition,
            "draft_saved": any(
                step.get("tool") == "create_support_case"
                and (step.get("result") or {}).get("status") == "created"
                for step in (trace or [])
            ),
            "active_case_id": state.active_case_id,
            "reply_preview": _reply_preview(reply),
        },
    }
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        stamp = started_at.strftime("%Y%m%dT%H%M%S")
        path = LOG_DIR / f"turn_{stamp}_{turn_id[:8]}.json"
        path.write_text(json.dumps(record, indent=2), encoding="utf-8")
        return path
    except OSError:
        return None
