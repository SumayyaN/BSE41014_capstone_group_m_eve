"""Offers the catalogue tools to Gemini and runs only the calls the app allows.

Week 4 shipped MAX_ROUNDS and the tool allow-list. Week 5 extends this into
the explicit Sense -> Plan/Decide -> Act -> Observe -> Stop/Re-plan loop from
the Agent Task Contract, Section 3, and closes the two gaps the Contract
(Section 9) names directly: no per-turn tool-call cap, and no per-session
draft cap. Everything below cites the Contract section it implements so the
mapping stays checkable during review.

retrieve_documents and create_support_case themselves are untouched -
tools/handlers.py and tools/case_store.py already do their job and are
already covered by the Week 4 failure/authorization test evidence. This file
only decides WHEN those tools may run and HOW MANY TIMES, and records why a
turn stopped.
"""

import re
from datetime import datetime, timezone

from google.genai import types

from agent.state import SessionState
from llm_client import client, load_prompt
from observability.turn_log import write_turn_log
from tools.case_store import blocked_topic, fee_decision, get_case_history
from tools.handlers import create_support_case, retrieve_documents

MODEL = "gemini-3.6-flash"

# --- Agent Task Contract, Section 5: Limits --------------------------------
# Enforced here, in application code. The model may REQUEST past these
# limits; the orchestration layer simply will not run the call.
MAX_ROUNDS = 3                 # model orchestration cycles per student turn
MAX_TOOL_CALLS_PER_TURN = 3    # search, a failed case call, and one correction
MAX_CASE_CALLS_PER_TURN = 2    # first create_support_case plus one correction
MAX_DRAFTS_PER_SESSION = 1     # create_support_case successes per session

# --- Agent Task Contract, Section 6: Stop conditions -----------------------
# Documented here so a stop_condition value on a result can be looked up
# without leaving this file. evidence/traces/run_trace.py cites these ids
# directly in the T1-T3 trace files.
STOP_CONDITIONS = {
    "S1": "Grounded answer - retrieve_documents returned ok, reply cites a source.",
    "S2": "Case drafted - create_support_case returned created; human hand-off.",
    "S3": "Unsupported / offer draft - retrieve_documents returned no_match.",
    "S4": "Out-of-scope refusal - student says they are continuing, returning, or postgraduate.",
    "S5": "Blocked topic refusal - admissions, grading, discipline, fee decision.",
    "S6": "Adversarial input refusal - instruction-override attempt, no tools run.",
    "S7": "Iteration limit - MAX_ROUNDS reached and no other stop applied.",
    "S8": "Tool failure after one retry - the latest result is still an error.",
}

RETRIEVE_DECLARATION = types.FunctionDeclaration(
    name="retrieve_documents",
    description=(
        "Search the approved freshman-onboarding documents. "
        "Returns at most 3 passages at or above similarity 0.70."
    ),
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "query": types.Schema(
                type=types.Type.STRING,
                description="The student's question or a shorter search query.",
            ),
            "top_k": types.Schema(
                type=types.Type.INTEGER,
                description="How many passages to return. Optional. Default 3. Maximum 3.",
            ),
        },
        required=["query"],
    ),
)

CASE_DECLARATION = types.FunctionDeclaration(
    name="create_support_case",
    description=(
        "Save a local support draft and a queue label. "
        "Does not contact an office. Call only after the student has agreed."
    ),
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "student_identifier": types.Schema(
                type=types.Type.STRING,
                description="Registration number. Two digits, U or X, four or five digits, optional /PS or /EVE.",
            ),
            "issue_summary": types.Schema(
                type=types.Type.STRING,
                description="Short description of the unresolved onboarding issue.",
            ),
            "category": types.Schema(
                type=types.Type.STRING,
                description="One of it_webmail_wifi, registration, fees_informational, accommodation, other_unclassified.",
            ),
        },
        required=["student_identifier", "issue_summary", "category"],
    ),
)

# Deterministic prompt-injection heuristic for Sense/S6. Deliberately narrow:
# it catches instruction-override phrasing, not every adversarial input (an
# admissions/grading request is still caught separately by blocked_topic/S5).
_OVERRIDE_RE = re.compile(
    r"\b(ignore (all|your|the)?\s*(previous|prior|above)?\s*instructions|"
    r"disregard (the|your) (system|above) prompt|"
    r"you are now|act as (if|though)|pretend (you|to)\b)",
    re.IGNORECASE,
)


def _looks_like_override_attempt(text: str) -> bool:
    return bool(_OVERRIDE_RE.search(text or ""))


# S4. Ordinary onboarding questions do not have to say "I am a freshman."
_NON_FRESHMAN_RE = re.compile(
    r"\b("
    r"not a freshman|not a first[- ]year|"
    r"post[- ]?graduate|"
    r"continuing student|returning student"
    r")\b",
    re.IGNORECASE,
)


def _says_not_a_freshman(text: str) -> bool:
    return bool(_NON_FRESHMAN_RE.search(text or ""))


# --- Week 6: case history recall -------------------------------------------
# The prior-case phrase must be in the current message. The registration
# number may be in that message or an earlier message from the student.
# The lookup reads drafts.json. It adds a note to the prompt and the turn
# continues. Assistant text is not searched, so an example number in a
# reply cannot be treated as the student's number.
_PRIOR_CASE_RE = re.compile(
    r"\b(already reported|my case|what happened to|still waiting|follow[- ]up on)\b",
    re.IGNORECASE,
)
_IDENTIFIER_RE = re.compile(r"\b\d{2}/[UX]/\d{4,5}(/(PS|EVE))?\b", re.IGNORECASE)


def _latest_student_identifier(state: SessionState) -> str | None:
    """Most recent registration number in the student's own messages."""
    for turn in reversed(state.conversation_history):
        if turn.get("role") != "user":
            continue
        match = _IDENTIFIER_RE.search(turn.get("content") or "")
        if match:
            return match.group(0).upper()
    return None


def _case_history_note(question: str, state: SessionState) -> str:
    """Prompt note for Case History Recall. Empty when this turn is not a recall."""
    if not _PRIOR_CASE_RE.search(question or ""):
        return ""
    identifier = _latest_student_identifier(state)
    if not identifier:
        return (
            "Session note: the student is asking about an earlier case and has "
            "not given a registration number in their own messages. Ask for the "
            "number they used when the case was filed. Do not invent an example number."
        )
    history = get_case_history(identifier)
    if not history:
        return (
            f"Session note: there is no case on file for {identifier}. "
            "Say that. Do not suggest the case was deleted because of its age."
        )
    lines = [
        f"Session note: this student ({identifier}) has {len(history)} existing case(s) on file."
    ]
    for record in history:
        lines.append(
            f"- {record.get('case_id')}, queue {record.get('queue_label')}, "
            f"opened {record.get('created_at')}. Issue: {record.get('issue_summary')}"
        )
    lines.append(
        "If this message is about the same issue, say that case already exists. "
        "Do not assign the case a live status, and do not tell the student they need not resubmit. "
        "The application refuses a second draft for this registration number."
    )
    return "\n".join(lines)


def _declarations(state: SessionState) -> list:
    """The allow-list the model sees this turn. create_support_case is
    withheld entirely - not just refused at call time - once agreement has
    not been given, or once this session already has a draft."""
    decls = [RETRIEVE_DECLARATION]
    if state.case_agreed and not state.draft_already_created():
        decls.append(CASE_DECLARATION)
    return decls


def _build_contents(state: SessionState) -> list:
    """Section 3, Sense: 'Load conversation_history ... and the new student
    message.' The new message is already the last entry in
    conversation_history by the time this is called (run_tool_turn records
    it first), so nothing further needs to be appended here."""
    contents = []
    for turn in state.conversation_history:
        role = "model" if turn["role"] == "assistant" else "user"
        contents.append(types.Content(role=role, parts=[types.Part(text=turn["content"])]))
    return contents


def _calls_and_text(response):
    candidates = getattr(response, "candidates", None) or []
    if not candidates or not candidates[0].content or not candidates[0].content.parts:
        return [], ""
    calls = []
    texts = []
    for part in candidates[0].content.parts:
        function_call = getattr(part, "function_call", None)
        if function_call and function_call.name:
            calls.append((function_call.name, dict(function_call.args or {})))
        elif getattr(part, "text", None):
            texts.append(part.text)
    return calls, "\n".join(texts).strip()


def _run_call(name: str, arguments: dict, state: SessionState, question: str) -> dict:
    """Act. The orchestration layer, not the model, decides whether a
    requested call actually runs (Section 2: 'the model may REQUEST a tool,
    but only the orchestration layer EXECUTES it')."""
    if name == "retrieve_documents":
        return retrieve_documents(arguments)

    if name == "create_support_case":
        if state.draft_already_created():
            return {
                "status": "error",
                "message": (
                    f"A support draft was already created this session "
                    f"({state.active_case_id}). Staff will follow up on that "
                    f"case; a second draft is not opened in the same session."
                ),
            }
        if not state.case_agreed or blocked_topic(question):
            return {
                "status": "error",
                "message": (
                    "The case tool is not available until the student agrees, "
                    "and it is refused for admissions, grading, and discipline."
                ),
            }
        existing = get_case_history(str(arguments.get("student_identifier") or ""))
        if existing:
            listed = "; ".join(
                f"{record.get('case_id')} ({record.get('issue_summary')})"
                for record in existing
            )
            return {
                "status": "error",
                "message": (
                    "A support draft is already on file for this registration "
                    f"number: {listed}. A second draft was not saved."
                ),
            }
        result = create_support_case(arguments, state.session_id)
        if result.get("status") == "created":
            state.active_case_id = result["case_id"]
        return result

    return {
        "status": "error",
        "message": "That action is not registered. Resolve, close, and reassign are not available.",
    }


def _reply_cites_returned_source(trace: list[dict], reply_text: str) -> bool:
    reply = (reply_text or "").lower()
    for step in trace:
        if step["tool"] != "retrieve_documents" or step["result"].get("status") != "ok":
            continue
        for chunk in step["result"].get("chunks") or []:
            title = (chunk.get("source_title") or "").strip()
            if title and title.lower() in reply:
                return True
    return False


def _infer_stop_condition(trace: list[dict], reply_text: str) -> str | None:
    """Label S1, S2, S3, or S8 from this turn's tool results and reply.
    S4 is not assigned here. S5 and S6 are assigned in Sense, before the model runs."""
    if not trace:
        return None
    if any(
        step["tool"] == "create_support_case" and step["result"].get("status") == "created"
        for step in trace
    ):
        return "S2"
    last = trace[-1]
    last_status = last["result"].get("status")
    if last_status in ("error", "validation_error"):
        attempts = sum(1 for step in trace if step["tool"] == last["tool"])
        if attempts >= 2:
            return "S8"
        return None
    if last["tool"] == "retrieve_documents" and last_status == "no_match":
        return "S3"
    if _reply_cites_returned_source(trace, reply_text):
        return "S1"
    return None


def run_tool_turn(state: SessionState, question: str) -> dict:
    """One student turn on the tool-enabled (v1.3) path. v1.2 retrieval is
    not used here. Implements the Contract, Section 3 loop in full:
    Sense -> Plan/Decide -> Act -> Observe -> Stop/Re-plan.
    """
    started_at = datetime.now(timezone.utc)
    state.reset_turn_counters()
    state.record_turn("user", question)

    # --- Sense --------------------------------------------------------
    if blocked_topic(question):
        return _stop(
            state, "S5",
            (
                "I can't help with admissions, grading, or disciplinary matters. "
                "Please contact the relevant university office."
            ),
            question=question,
            started_at=started_at,
        )
    if fee_decision(question):
        return _stop(
            state, "S5",
            (
                "I can't approve, waive, or refund a fee. "
                "I can explain general fee information, or save a question for staff, "
                "if you ask that separately."
            ),
            question=question,
            started_at=started_at,
        )
    if _says_not_a_freshman(question):
        return _stop(
            state, "S4",
            (
                "This assistant is for freshman onboarding. "
                "Please contact the office that handles continuing, returning, "
                "or postgraduate students."
            ),
            question=question,
            started_at=started_at,
        )
    if _looks_like_override_attempt(question):
        return _stop(
            state, "S6",
            (
                "I can't follow instructions embedded in a message that try to "
                "change how I'm allowed to behave. How can I help with your "
                "onboarding question?"
            ),
            question=question,
            started_at=started_at,
        )

    system_prompt = load_prompt("v1.3")
    history_note = _case_history_note(question, state)
    case_history_note = bool(history_note)
    if history_note:
        system_prompt += "\n\n" + history_note
    if state.draft_already_created():
        # v1.3_tools.txt only tells the model what to say when the student
        # has not yet agreed ("ask the student to use the agreement
        # control"). It says nothing about the Week 5 per-session draft cap,
        # so once create_support_case is withheld from _declarations below,
        # the model has no guidance for that state and would fall back to
        # that same "please agree" line - wrong and confusing to a student
        # who already agreed and already has an open case. Append a short,
        # state-derived note the same way llm_client.py's
        # build_context_block injects retrieved chunks: deterministic code
        # supplies the fact, the model still owns the wording.
        system_prompt += (
            "\n\nSession note: this chat already has a support draft on "
            f"file, case {state.active_case_id}. create_support_case is not "
            "offered again this session. If the student asks to open "
            "another case, tell them this case is already logged and that "
            "staff will follow up on it - do not ask them to use the "
            "agreement control again, since they already used it."
        )
    contents = _build_contents(state)
    tool = types.Tool(function_declarations=_declarations(state))

    turn_trace = []
    calls_this_turn = 0
    case_calls_this_turn = 0
    text = ""
    hit_round_limit = True

    for _ in range(MAX_ROUNDS):
        state.iteration_count += 1

        # --- Plan / Decide ---------------------------------------------
        try:
            response = client.models.generate_content(
                model=MODEL,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    tools=[tool],
                ),
            )
        except Exception as exc:
            return _model_failure(
                state,
                turn_trace,
                exc,
                question=question,
                started_at=started_at,
                case_history_note=case_history_note,
            )
        calls, text = _calls_and_text(response)
        if not calls:
            hit_round_limit = False
            break

        contents.append(response.candidates[0].content)
        response_parts = []
        for name, arguments in calls:
            # --- Act -----------------------------------------------------
            if calls_this_turn >= MAX_TOOL_CALLS_PER_TURN:
                result = {
                    "status": "error",
                    "message": (
                        "You've reached the maximum number of actions for "
                        "this turn. Tell the student to ask again in a new "
                        "message if they still need help."
                    ),
                }
            elif name == "create_support_case" and case_calls_this_turn >= MAX_CASE_CALLS_PER_TURN:
                result = {
                    "status": "error",
                    "message": (
                        "A case field was already corrected once this turn. "
                        "Ask the student to send the corrected details in a new message."
                    ),
                }
            else:
                result = _run_call(name, arguments, state, question)
                calls_this_turn += 1
                if name == "create_support_case":
                    case_calls_this_turn += 1

            # --- Observe ---------------------------------------------------
            state.log_tool_call(name, arguments, result)
            turn_trace.append({"tool": name, "arguments": arguments, "result": result})
            if name == "retrieve_documents" and result.get("status") == "ok":
                state.retrieved_context = result["chunks"]

            response_parts.append(
                types.Part.from_function_response(name=name, response=result)
            )
        contents.append(types.Content(role="user", parts=response_parts))

    # --- Stop / Re-plan -------------------------------------------------
    if not text:
        # No final reply text was produced - typically because the model
        # spent its last allowed round on a tool call and never got a
        # further round to phrase a response. Before falling back to a
        # generic apology, check whether a tool nonetheless succeeded: the
        # Week 4 test evidence flagged exactly this failure mode (a student
        # shown an error message while their case had, in fact, been
        # created), and the orchestration layer must not repeat it.
        inferred = _infer_stop_condition(turn_trace, "")
        found_passages = any(
            step["tool"] == "retrieve_documents" and step["result"].get("status") == "ok"
            for step in turn_trace
        )
        if inferred == "S2":
            created_step = next(
                step for step in reversed(turn_trace)
                if step["tool"] == "create_support_case" and step["result"].get("status") == "created"
            )
            case_id = created_step["result"].get("case_id")
            text = (
                f"I've saved this as a support draft (case {case_id}); "
                f"a staff member will follow up with you."
            )
            stop_condition = "S2"
        elif inferred == "S8":
            text = (
                "I tried that twice and it still failed. "
                "Please send the corrected details in a new message."
            )
            stop_condition = "S8"
        elif inferred == "S3":
            text = (
                "I couldn't find this in the approved documents. "
                "I can save a support draft if you use the agreement button."
            )
            stop_condition = "S3"
        elif found_passages:
            text = (
                "I found relevant information but ran out of turns to phrase "
                "a full reply. Please ask again and I'll answer directly "
                "from what I found."
            )
            stop_condition = "S7"
        else:
            text = (
                "I wasn't able to finish that within this turn's limits. "
                "Could you try rephrasing, or ask again?"
            )
            stop_condition = "S7"
    elif hit_round_limit:
        stop_condition = _infer_stop_condition(turn_trace, text) or "S7"
    else:
        stop_condition = _infer_stop_condition(turn_trace, text)

    state.record_turn("assistant", text)
    return _finish_turn(
        state,
        question=question,
        text=text,
        turn_trace=turn_trace,
        stop_condition=stop_condition,
        started_at=started_at,
        case_history_note=case_history_note,
    )


def _finish_turn(
    state: SessionState,
    *,
    question: str,
    text: str,
    turn_trace: list[dict],
    stop_condition: str | None,
    started_at: datetime,
    case_history_note: bool = False,
    error: str | None = None,
) -> dict:
    """Write the Week 7 turn log, then return the same shape callers already use."""
    write_turn_log(
        state,
        student_message=question,
        reply=text,
        stop_condition=stop_condition,
        trace=turn_trace,
        started_at=started_at,
        case_history_note=case_history_note,
        error=error,
    )
    return {
        "text": text,
        "trace": turn_trace,
        "stop_condition": stop_condition,
        "iteration_count": state.iteration_count,
    }


def _model_failure(
    state: SessionState,
    trace: list[dict],
    exc: Exception,
    *,
    question: str,
    started_at: datetime,
    case_history_note: bool = False,
) -> dict:
    """The model call failed after the student message was stored. Record an
    assistant turn so the next message is not a second user turn in a row.
    If this turn already saved a draft, say so."""
    case_id = next(
        (
            step["result"].get("case_id")
            for step in reversed(trace)
            if step["tool"] == "create_support_case" and step["result"].get("status") == "created"
        ),
        None,
    )
    text = f"Error: {exc}"
    stop_condition = None
    if case_id:
        text += (
            f" A support draft was already saved (case {case_id}). "
            "A staff member will follow up on it."
        )
        stop_condition = "S2"
    state.record_turn("assistant", text)
    return _finish_turn(
        state,
        question=question,
        text=text,
        turn_trace=trace,
        stop_condition=stop_condition,
        started_at=started_at,
        case_history_note=case_history_note,
        error=str(exc),
    )


def _stop(
    state: SessionState,
    stop_condition: str,
    text: str,
    *,
    question: str,
    started_at: datetime,
) -> dict:
    """Used by Sense when a deterministic check ends the turn before the
    model is ever called - no tools run, no iteration spent."""
    state.record_turn("assistant", text)
    return _finish_turn(
        state,
        question=question,
        text=text,
        turn_trace=[],
        stop_condition=stop_condition,
        started_at=started_at,
    )