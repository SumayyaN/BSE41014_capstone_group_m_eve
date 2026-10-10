"""Session-scoped state for the bounded agent workflow.

This is exactly the state list in the Agent Task Contract, Section 4 - no
more, no less. All of it is session-scoped (Streamlit session / application
session_id) and is cleared when the session ends. Persistent memory across
browser sessions is explicitly out of scope for Week 5 (see the Contract,
Section 4 and Section 7) and is planned for Week 6 per the Project Charter.

Nothing in this file talks to Gemini or to the tool handlers directly. It is
plain, deterministic bookkeeping, which is what lets tools/orchestrate.py
enforce the Contract's Section 5 limits (max drafts per session, max tool
calls per turn) by asking this object a question, rather than trusting the
model to remember or self-police those limits.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class SessionState:
    # Assigned once per chat session. Ties every draft this session creates
    # back to the same session_id - the model never sets this itself
    # (see tools/case_store.py: create_draft trusts only the session_id it
    # is called with, not anything supplied in the model's arguments).
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # Ordered {"role": "user" | "assistant", "content": str} turns for this
    # session. Fed to the model as multi-turn context in Sense/Plan so a
    # follow-up question ("what about registration?") is understood without
    # the student having to repeat themselves.
    conversation_history: list[dict] = field(default_factory=list)

    # True only after the student uses the sidebar agreement control. Free
    # text such as "yes" or "go ahead" must never set this - see
    # tools/orchestrate.py, which reads this flag but never writes it from
    # model output.
    case_agreed: bool = False

    # case_id of the draft created in this session, if any. Doubles as the
    # Section 5 "max 1 support draft per session" gate: once this is set,
    # create_support_case is refused and the student is pointed back to this
    # id instead of a new draft being opened.
    active_case_id: str | None = None

    # Chunks from the most recent successful retrieve_documents call, kept
    # for grounding follow-up questions and for inclusion in execution
    # traces. Not sent back to the model automatically - retrieval happens
    # fresh via the tool on each turn that needs it.
    retrieved_context: list[dict] = field(default_factory=list)

    # Number of model orchestration cycles (Plan/Decide -> Act -> Observe
    # rounds) run in the CURRENT student turn. Reset at the start of every
    # turn; run_tool_turn increments it once per model call, capped by
    # MAX_ROUNDS in tools/orchestrate.py.
    iteration_count: int = 0

    # Ordered {timestamp, tool, arguments, result} entries for the WHOLE
    # session (not reset per turn). This is the audit trail Section 4 calls
    # for, and it is what evidence/traces/run_trace.py reads to write the
    # Week 5 T1-T3 execution traces.
    tool_call_log: list[dict] = field(default_factory=list)

    def draft_already_created(self) -> bool:
        """Section 5: at most one support draft per session."""
        return self.active_case_id is not None

    def log_tool_call(self, tool: str, arguments: dict, result: dict) -> None:
        self.tool_call_log.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tool": tool,
            "arguments": arguments,
            "result": result,
        })

    def record_turn(self, role: str, content: str) -> None:
        self.conversation_history.append({"role": role, "content": content})

    def reset_turn_counters(self) -> None:
        """Called once at the start of every student turn. Only the
        per-turn iteration count resets - tool_call_log, conversation
        history, and the draft/agreement flags persist for the session."""
        self.iteration_count = 0