"""Offers the catalogue tools to Gemini and runs only the calls the app allows.

Week 4 shipped MAX_ROUNDS and the tool allow-list. Week 5 extends this into
the explicit Sense -> Plan/Decide -> Act -> Observe -> Stop/Re-plan loop from
the Agent Task Contract, Section 3, and closes the gaps the Contract names
directly: no per-turn tool-call cap, no per-session draft cap, no deterministic
check for a fee-decision or non-freshman request before any tool runs, and no
safe recovery when Gemini itself fails mid-turn. This version also folds in a
contract review pass with six corrections (see the comment above each one
below, each starting "Review:").

retrieve_documents and create_support_case themselves are untouched -
tools/handlers.py and tools/case_store.py already do their job and are
already covered by the Week 4 failure/authorization test evidence. This file
only decides WHEN those tools may run and HOW MANY TIMES, and records why a
turn stopped.
"""

import re

from google.genai import types

from agent.state import SessionState
from llm_client import client, load_prompt
from tools.case_store import blocked_topic, fee_decision
from tools.handlers import create_support_case, retrieve_documents

MODEL = "gemini-3.6-flash"

# --- Agent Task Contract, Section 5: Limits --------------------------------
# Enforced here, in application code. The model may REQUEST past these
# limits; the orchestration layer simply will not run the call.
#
# Review: three tool calls are now allowed in one turn (was two), so a turn
# can search, reject a bad registration number, and accept one correction -
# one retrieve_documents call plus two create_support_case attempts. A
# fourth call of any kind this turn is refused.
MAX_ROUNDS = 3                      # model orchestration cycles per student turn
MAX_TOOL_CALLS_PER_TURN = 3         # total tool calls across the whole turn
# Review: create_support_case keeps its OWN, tighter cap even though the
# overall budget above is now 3. A third attempt to save a case in the same
# turn is refused even if the overall budget has room left - this preserves
# the "first attempt + one retry" meaning of a case-save specifically.
MAX_CASE_ATTEMPTS_PER_TURN = 2
MAX_DRAFTS_PER_SESSION = 1          # create_support_case successes per session

# --- Agent Task Contract, Section 6: Stop conditions -----------------------
# Documented here so a stop_condition value on a result can be looked up
# without leaving this file. evidence/traces/run_trace.py cites these ids
# directly in the T1-T3 trace files.
STOP_CONDITIONS = {
    # Review: S1 requires the reply to actually NAME a source the search
    # returned - retrieve_documents returning "ok" is necessary but not
    # sufficient on its own.
    "S1": "Grounded answer - retrieve_documents returned ok AND the reply names a source it actually returned.",
    "S2": "Case drafted - create_support_case returned created; human hand-off.",
    "S3": "Unsupported / offer draft - retrieve_documents returned no_match.",
    # Review: now checked deterministically in Sense - a student who states
    # non-freshman status (continuing/returning/postgraduate, or an explicit
    # year-of-study declaration) stops the turn before any tool runs.
    "S4": "Out-of-scope refusal - student states non-freshman status; checked before any tool runs.",
    # Review: a fee decision (waive/refund/approve/cancel) is now also
    # checked in Sense, before any tool runs - not only inside
    # create_support_case's own validation as before.
    "S5": "Blocked topic refusal - admissions, grading, discipline, or a fee decision; checked before any tool runs.",
    "S6": "Adversarial input refusal - instruction-override attempt, no tools run.",
    "S7": "Iteration limit - MAX_ROUNDS reached without S1/S2.",
    # Review: S8 requires a GENUINE retry - at least two attempts of the
    # SAME tool this turn, with the most recent one still failing. A single,
    # unretried failure is not S8 (left unclassified instead).
    "S8": "Tool failure after a retry - a second attempt of the same tool was made this turn and it still failed.",
    # Not one of the Contract's S-codes. A distinct failure mode: Gemini
    # itself raised mid-turn (network/429/503/etc.), as opposed to a tool
    # returning a structured error result (which is what S8 is about).
    "ERROR": "Uncaught model/API failure mid-turn - not an official Contract stop code.",
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

# Review (S4): deterministic non-freshman self-identification check, run in
# Sense before any tool call. Deliberately narrow, same spirit as
# blocked_topic/fee_decision in tools/case_store.py - it only catches an
# EXPLICIT statement of non-freshman status, matching the known detection
# gap documented in the Week 2 progress report ("US-10's non-freshman
# redirection only triggers when a student explicitly states their status").
# It does not attempt to infer year of study from context.
_NON_FRESHMAN_RE = re.compile(
    r"\b(i'?m|i am|as a)\s+(a\s+)?(2nd|3rd|4th|5th|second|third|fourth|fifth|final)[\s-]*year\b|"
    r"\bcontinuing student\b|\breturning student\b|\bpost-?graduate\b|"
    r"\bnot a freshman\b|\bnot a first[\s-]?year\b",
    re.IGNORECASE,
)


def _looks_like_override_attempt(text: str) -> bool:
    return bool(_OVERRIDE_RE.search(text or ""))


def _looks_like_non_freshman(text: str) -> bool:
    return bool(_NON_FRESHMAN_RE.search(text or ""))


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
        if not state.case_agreed or blocked_topic(question) or fee_decision(question):
            return {
                "status": "error",
                "message": (
                    "The case tool is not available until the student agrees, "
                    "and it is refused for admissions, grading, discipline, "
                    "and fee decisions."
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


def _names_a_returned_source(text: str, chunks: list[dict]) -> bool:
    """Review (S1): the reply must actually mention a source the search
    returned, not merely follow a successful retrieve_documents call."""
    lowered = (text or "").lower()
    return any(
        (chunk.get("source_title") or "").lower() in lowered
        for chunk in chunks
        if chunk.get("source_title")
    )


def _infer_stop_condition(trace: list[dict], text: str) -> str | None:
    """Label the turn's outcome from its LAST tool action (what the final
    reply was actually based on), not from scanning the whole trace for any
    matching result. This also fixes a prior bug: scanning the whole trace
    could label a turn S2 because an EARLIER step created a case, even if a
    LATER step in the same turn failed.

    Review (S8): a failure is only S8 if it is the SECOND (or later) attempt
    of that same tool this turn. A lone, unretried failure returns None
    instead - a human should look at the transcript rather than have it
    mislabeled.

    Review (S1): a successful retrieve_documents call is only S1 if the
    reply actually names one of the returned sources.

    This does NOT attempt to guess S4 or S6 after the fact - those are
    caught in Sense, deterministically, before any tool runs; if Sense did
    not catch them, this function correctly returns None rather than
    guessing from the model's wording.
    """
    if not trace:
        return None

    last_step = trace[-1]
    last_tool = last_step["tool"]
    last_result = last_step["result"]
    attempts_for_last_tool = sum(1 for step in trace if step["tool"] == last_tool)

    if last_tool == "create_support_case" and last_result.get("status") == "created":
        return "S2"

    if last_result.get("status") in ("error", "validation_error"):
        if attempts_for_last_tool >= 2:
            return "S8"
        return None

    if last_tool == "retrieve_documents" and last_result.get("status") == "no_match":
        return "S3"

    if last_tool == "retrieve_documents" and last_result.get("status") == "ok":
        if _names_a_returned_source(text, last_result.get("chunks", [])):
            return "S1"
        return None

    return None


def _stop(state: SessionState, stop_condition: str, text: str, trace: list[dict] | None = None) -> dict:
    """Used by Sense when a deterministic check ends the turn before the
    model is ever called - no tools run (unless trace is passed in, used
    only by the mid-turn error path below), no further iteration spent."""
    state.record_turn("assistant", text)
    return {
        "text": text,
        "trace": trace or [],
        "stop_condition": stop_condition,
        "iteration_count": state.iteration_count,
    }


def run_tool_turn(state: SessionState, question: str) -> dict:
    """One student turn on the tool-enabled (v1.3) path. v1.2 retrieval is
    not used here. Implements the Contract, Section 3 loop in full:
    Sense -> Plan/Decide -> Act -> Observe -> Stop/Re-plan.
    """
    state.reset_turn_counters()
    state.record_turn("user", question)

    # --- Sense --------------------------------------------------------
    if blocked_topic(question):
        return _stop(state, "S5", (
            "I can't help with admissions, grading, or disciplinary matters. "
            "Please contact the relevant university office."
        ))
    # Review: a fee decision (waive/refund/approve/cancel) is refused here,
    # before any tool runs - previously this was only checked inside
    # create_support_case's own validation, after retrieve_documents could
    # already have run for the same message.
    if fee_decision(question):
        return _stop(state, "S5", (
            "I can't waive, refund, approve, or otherwise decide a fee "
            "question. I can log it as an informational case for the fees "
            "office if you'd like, once you agree."
        ))
    # Review: an explicit non-freshman statement stops the turn here, before
    # any tool runs, rather than being left entirely to the model.
    if _looks_like_non_freshman(question):
        return _stop(state, "S4", (
            "This assistant only supports Makerere freshman onboarding "
            "questions. Please contact your faculty/department office or "
            "the relevant student support channel for your situation."
        ))
    if _looks_like_override_attempt(question):
        return _stop(state, "S6", (
            "I can't follow instructions embedded in a message that try to "
            "change how I'm allowed to behave. How can I help with your "
            "onboarding question?"
        ))

    system_prompt = load_prompt("v1.3")
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

    # Review: Gemini itself can fail mid-turn (network error, 429, 503).
    # Previously an uncaught exception propagated out of run_tool_turn,
    # which meant the assistant's turn was never recorded into
    # conversation_history even though the student's message already had
    # been - so the NEXT call would send two consecutive "user" turns to the
    # model. Catching it here keeps every turn paired: one user entry, one
    # assistant entry, always, even on failure.
    try:
        for _ in range(MAX_ROUNDS):
            state.iteration_count += 1

            # --- Plan / Decide ---------------------------------------------
            response = client.models.generate_content(
                model=MODEL,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    tools=[tool],
                ),
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
                elif name == "create_support_case" and case_calls_this_turn >= MAX_CASE_ATTEMPTS_PER_TURN:
                    result = {
                        "status": "error",
                        "message": (
                            "A case save has already been attempted twice "
                            "this turn. Tell the student to try again in a "
                            "new message if the details still need fixing."
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
    except Exception:
        if state.active_case_id:
            text = (
                f"Something went wrong on my end before I could finish "
                f"replying. Your case was already saved as "
                f"{state.active_case_id}, so a staff member will still "
                f"follow up on it. Please try your next message again."
            )
        else:
            text = "Something went wrong on my end. Please try again in a moment."
        return _stop(state, "ERROR", text, trace=turn_trace)

    # --- Stop / Re-plan -------------------------------------------------
    if not text:
        # No final reply text was produced - typically because the model
        # spent its last allowed round on a tool call and never got a
        # further round to phrase a response. Before falling back to a
        # generic apology, check the LAST tool outcome directly: the Week 4
        # test evidence flagged exactly this failure mode (a student shown
        # an error message while their case had, in fact, been created),
        # and the orchestration layer must not repeat it.
        last_step = turn_trace[-1] if turn_trace else None
        if last_step and last_step["tool"] == "create_support_case" and last_step["result"].get("status") == "created":
            case_id = last_step["result"].get("case_id")
            text = (
                f"I've saved this as a support draft (case {case_id}); "
                f"a staff member will follow up with you."
            )
            stop_condition = "S2"
        elif last_step and last_step["tool"] == "retrieve_documents" and last_step["result"].get("status") == "ok":
            text = (
                "I found relevant information but ran out of turns to phrase "
                "a full reply - please ask again and I'll answer directly "
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
        stop_condition = "S7"
    else:
        stop_condition = _infer_stop_condition(turn_trace, text)

    state.record_turn("assistant", text)
    return {
        "text": text,
        "trace": turn_trace,
        "stop_condition": stop_condition,
        "iteration_count": state.iteration_count,
    }