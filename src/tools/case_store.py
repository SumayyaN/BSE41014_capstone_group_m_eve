"""Local support drafts. The application owns ids, validation, and queue labels."""

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from rag.memory import remember_case

STORE_PATH = Path(__file__).resolve().parents[2] / "data" / "cases" / "drafts.json"

REGISTRATION_RE = re.compile(r"^\d{2}/[UX]/\d{4,5}(/(PS|EVE))?$")

QUEUE_MAP = {
    "it_webmail_wifi": "ict_helpdesk",
    "registration": "registration_office",
    "fees_informational": "fees_information",
    "accommodation": "accommodation_office",
    "other_unclassified": "general_onboarding",
}

BLOCKED_TOPIC_RE = re.compile(
    r"\b(admissions?|grading|grades?|gpa|disciplinary|discipline|suspension|misconduct)\b",
    re.IGNORECASE,
)
FEE_DECISION_RE = re.compile(
    r"\b(waive|waived|refund|approve my fee|cancel my fee|fee decision)\b",
    re.IGNORECASE,
)


def blocked_topic(text: str) -> bool:
    return bool(BLOCKED_TOPIC_RE.search(text or ""))


def fee_decision(text: str) -> bool:
    return bool(FEE_DECISION_RE.search(text or ""))


def _load() -> list[dict]:
    if not STORE_PATH.exists():
        return []
    return json.loads(STORE_PATH.read_text(encoding="utf-8"))


def _save(records: list[dict]) -> None:
    STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STORE_PATH.write_text(json.dumps(records, indent=2), encoding="utf-8")


def _next_case_id(records: list[dict]) -> str:
    year = datetime.now(timezone.utc).year
    prefix = f"CASE-{year}-"
    numbers = []
    for record in records:
        case_id = record.get("case_id", "")
        if case_id.startswith(prefix):
            try:
                numbers.append(int(case_id.removeprefix(prefix)))
            except ValueError:
                continue
    nxt = (max(numbers) + 1) if numbers else 1
    return f"{prefix}{nxt:06d}"


def create_draft(arguments: dict, session_id: str) -> dict:
    """Validate a case request and store a draft. Never trusts model-set ids."""
    if not session_id:
        return {
            "status": "error",
            "message": "This chat has no application session id, so no draft was saved.",
        }

    summary = str(arguments.get("issue_summary") or "").strip()
    identifier = str(arguments.get("student_identifier") or "").strip().upper()
    category = str(arguments.get("category") or "").strip()

    if blocked_topic(summary):
        return {
            "status": "error",
            "message": "Admissions, grading, and disciplinary matters are not filed as drafts.",
        }
    if category == "fees_informational" and fee_decision(summary):
        return {
            "status": "error",
            "message": "A fee draft may record a question. It must not record a fee decision.",
        }

    errors = []
    if not identifier:
        errors.append({"field": "student_identifier", "message": "student_identifier is required"})
    elif not REGISTRATION_RE.match(identifier):
        errors.append({
            "field": "student_identifier",
            "message": "Use two digits, U or X, four or five digits, and optionally /PS or /EVE.",
        })
    if not summary:
        errors.append({"field": "issue_summary", "message": "issue_summary is required"})
    if category not in QUEUE_MAP:
        errors.append({
            "field": "category",
            "message": "category must be one of: " + ", ".join(QUEUE_MAP),
        })
    if errors:
        return {"status": "validation_error", "validation_errors": errors}

    queue = QUEUE_MAP.get(category)
    if not queue:
        records = _load()
        case_id = _next_case_id(records)
        record = {
            "case_id": case_id,
            "session_id": session_id,
            "student_identifier": identifier,
            "issue_summary": summary,
            "category": category,
            "queue_label": "manual_review",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        records.append(record)
        _save(records)
        return {"status": "error", "message": "No queue mapping for this category. Draft stored for manual review."}

    records = _load()
    case_id = _next_case_id(records)
    created_at = datetime.now(timezone.utc).isoformat()
    records.append({
        "case_id": case_id,
        "session_id": session_id,
        "student_identifier": identifier,
        "issue_summary": summary,
        "category": category,
        "queue_label": queue,
        "created_at": created_at,
    })
    _save(records)

    # Week 6: persist the most recent case for this student so future
    # sessions can answer "what happened to my case?" without asking the
    # student to repeat the case_id.
    remember_case(student_id=identifier, case_id=case_id, topic=category)

    return {
        "status": "created",
        "case_id": case_id,
        "session_id": session_id,
        "routed_queue": queue,
        "created_at": created_at,
    }