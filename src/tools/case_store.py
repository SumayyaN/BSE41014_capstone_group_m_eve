"""Local support drafts. The application owns ids, validation, and queue labels."""

import json
import re
from datetime import datetime, timezone
from pathlib import Path

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


_POLICY_QUESTION_RE = re.compile(
    r"\b(what does|what do|which documents|code of conduct|according to|"
    r"say about|says about|admission letter)\b",
    re.IGNORECASE,
)
_PLACEHOLDER_RE = re.compile(
    r"^(unspecified( onboarding issue)?|something is wrong|n/?a|none|test|placeholder|x)$",
    re.IGNORECASE,
)


def blocked_topic(text: str) -> bool:
    """Refuse admissions, grading, and discipline decisions.

    A question that asks what a policy document says is not a decision,
    so it is allowed through to retrieval.
    """
    message = text or ""
    if not BLOCKED_TOPIC_RE.search(message):
        return False
    if _POLICY_QUESTION_RE.search(message):
        return False
    return True


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
    if fee_decision(summary):
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
    elif len(summary) < 8 or _PLACEHOLDER_RE.match(summary):
        errors.append({
            "field": "issue_summary",
            "message": "Describe the onboarding issue in a short sentence. A placeholder is not enough.",
        })
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

    return {
        "status": "created",
        "case_id": case_id,
        "session_id": session_id,
        "routed_queue": queue,
        "created_at": created_at,
    }


def get_case_history(student_identifier: str) -> list[dict]:
    """Read drafts for one registration number. Exact match only.

    Returns [] when the number is missing, malformed, or not on file.
    Does not create a second store and does not delete old drafts.
    """
    identifier = str(student_identifier or "").strip().upper()
    if not identifier or not REGISTRATION_RE.match(identifier):
        return []
    return [
        record for record in _load()
        if str(record.get("student_identifier") or "").upper() == identifier
    ]