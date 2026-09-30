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

from google.genai import types

from agent.state import SessionState
from llm_client import client, load_prompt
from tools.case_store import blocked_topic
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
    "S4": "Out-of-scope refusal - non-freshman or non-onboarding request.",
    "S5": "Blocked topic refusal - admissions, grading, discipline, fee decision.",
    "S6": "Adversarial input refusal - instruction-override attempt, no tools run.",
    "S7": "Iteration limit - MAX_ROUNDS reached without S1/S2.",
    "S8": "Tool failure after one retry - error/validation_error persisted.",
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
        result = create_support_case(arguments, state.session_id)
        if result.get("status") == "created":
            state.active_case_id = result["case_id"]
        return result

    return {
        "status": "error",
        "message": "That action is not registered. Resolve, close, and reassign are not available.",
    }


def _infer_stop_condition(trace: list[dict]) -> str | None:
    """Best-effort label for S1/S2/S3/S8, read off the tool results actually
    produced this turn. This does NOT attempt to guess S4 (out-of-scope) or
    S6 (adversarial) when no deterministic check caught them in Sense - those
    depend on reading the reply's wording, which is exactly the kind of
    judgment call this project keeps with a person rather than automating.
    A trace author should assign S4 by hand if the transcript is a refusal
    but no tool ran and Sense did not already tag S5/S6."""
    for step in reversed(trace):
        result = step["result"]
        if step["tool"] == "create_support_case" and result.get("status") == "created":
            return "S2"
        if result.get("status") in ("error", "validation_error"):
            return "S8"
        if step["tool"] == "retrieve_documents" and result.get("status") == "no_match":
            return "S3"
        if step["tool"] == "retrieve_documents" and result.get("status") == "ok":
            return "S1"
    return None


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
        inferred = _infer_stop_condition(turn_trace)
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
        elif inferred == "S1":
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
        stop_condition = _infer_stop_condition(turn_trace)

    state.record_turn("assistant", text)
    return {
        "text": text,
        "trace": turn_trace,
        "stop_condition": stop_condition,
        "iteration_count": state.iteration_count,
    }


def _stop(state: SessionState, stop_condition: str, text: str) -> dict:
    """Used by Sense when a deterministic check ends the turn before the
    model is ever called - no tools run, no iteration spent."""
    state.record_turn("assistant", text)
    return {
        "text": text,
        "trace": [],
        "stop_condition": stop_condition,
        "iteration_count": state.iteration_count,
    }
