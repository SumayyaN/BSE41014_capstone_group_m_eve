"""
Persistent memory for the freshman support agent.

Only one thing is remembered across sessions per student:
  - the most recent case_id
  - the case topic
  - the case status (always "draft" for now)
  - the timestamp of last interaction

Memory is stored as a single JSON file and is never sent wholesale
to the model. Only the current student's entry is ever included in a prompt.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

MEMORY_PATH = Path(__file__).resolve().parents[2] / "data" / "memory" / "memory.json"
MEMORY_PATH.parent.mkdir(parents=True, exist_ok=True)

RETENTION_DAYS = 90


def _load() -> dict:
    if not MEMORY_PATH.exists():
        return {}
    try:
        return json.loads(MEMORY_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _save(data: dict) -> None:
    MEMORY_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _purge_expired(data: dict) -> dict:
    """Remove entries older than RETENTION_DAYS."""
    now = datetime.now(timezone.utc)
    kept = {}
    for student_id, entry in data.items():
        try:
            last_seen = datetime.fromisoformat(entry["last_seen"])
            if (now - last_seen).days < RETENTION_DAYS:
                kept[student_id] = entry
        except Exception:
            continue
    return kept


def remember_case(student_id: str, case_id: str, topic: str) -> None:
    """Record the most recent case for this student."""
    data = _purge_expired(_load())
    data[student_id] = {
        "last_case_id": case_id,
        "last_case_topic": topic,
        "last_case_status": "draft",
        "last_seen": datetime.now(timezone.utc).isoformat(),
    }
    _save(data)


def recall_case(student_id: str) -> dict | None:
    """Return the most recent case for this student, or None."""
    data = _purge_expired(_load())
    return data.get(student_id)


def forget_student(student_id: str) -> bool:
    """Delete all memory for a student. Returns True if anything was removed."""
    data = _load()
    if student_id in data:
        del data[student_id]
        _save(data)
        return True
    return False


if __name__ == "__main__":
    # Quick manual test
    remember_case("2024-99999", "CASE-2026-TEST", "Webmail")
    print("Stored:", recall_case("2024-99999"))
    print("Forgotten:", forget_student("2024-99999"))
    print("After forget:", recall_case("2024-99999"))