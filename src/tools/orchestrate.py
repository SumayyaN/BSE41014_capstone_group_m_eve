"""Offers the catalogue tools to Gemini and runs only the calls the app allows."""

from google.genai import types

from llm_client import client, load_prompt
from tools.case_store import blocked_topic
from tools.handlers import create_support_case, retrieve_documents

MODEL = "gemini-3.6-flash"
MAX_ROUNDS = 3

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


def _declarations(case_agreed: bool) -> list:
    names = [RETRIEVE_DECLARATION]
    if case_agreed:
        names.append(CASE_DECLARATION)
    return names


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


def _run_call(name: str, arguments: dict, session_id: str, case_agreed: bool, question: str) -> dict:
    if name == "retrieve_documents":
        return retrieve_documents(arguments)
    if name == "create_support_case":
        if not case_agreed or blocked_topic(question):
            return {
                "status": "error",
                "message": "The case tool is not available until the student agrees, and it is refused for admissions, grading, and discipline.",
            }
        return create_support_case(arguments, session_id)
    return {
        "status": "error",
        "message": "That action is not registered. Resolve, close, and reassign are not available.",
    }


def run_tool_turn(question: str, session_id: str, case_agreed: bool) -> dict:
    """One student message on the tool-enabled path. v1.2 retrieval is not used here."""
    if blocked_topic(question):
        return {
            "text": (
                "I can't help with admissions, grading, or disciplinary matters. "
                "Please contact the relevant university office."
            ),
            "trace": [],
        }

    system_prompt = load_prompt("v1.3")
    contents = [types.Content(role="user", parts=[types.Part(text=question)])]
    tool = types.Tool(function_declarations=_declarations(case_agreed))
    trace = []
    text = ""

    for _ in range(MAX_ROUNDS):
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
            break

        contents.append(response.candidates[0].content)
        response_parts = []
        for name, arguments in calls:
            result = _run_call(name, arguments, session_id, case_agreed, question)
            trace.append({"tool": name, "arguments": arguments, "result": result})
            response_parts.append(
                types.Part.from_function_response(name=name, response=result)
            )
        contents.append(types.Content(role="user", parts=response_parts))

    if not text:
        text = "I could not complete that request."
    return {"text": text, "trace": trace}
