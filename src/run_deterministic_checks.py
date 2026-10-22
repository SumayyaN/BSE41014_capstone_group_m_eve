"""Week 7: deterministic scenario checks (no Gemini calls, no network, no quota).

Run from the repo's src/ folder:

    python run_deterministic_checks.py

It exercises your real handlers.py, case_store.py, state.py and orchestrate.py.
Only two things are replaced: the Gemini model (a scripted fake that returns the
tool calls each scenario needs) and the retrieval function (for the failure
scenarios). Drafts go to a temporary file, never to data/cases/drafts.json.

Output: a PASS/FAIL line per scenario and deterministic_results.json, which you
can paste into the evaluation sheet (columns "Actual output / evidence" and
"Result").
"""
import json
import pathlib
import tempfile
from types import SimpleNamespace as NS

from agent.state import SessionState
from tools import case_store, handlers
import tools.orchestrate as orch

RESULTS: dict[str, dict] = {}
ORIG_RETRIEVE = handlers.retrieve


# ---------------------------------------------------------------- helpers
def fresh_store(seed=None) -> pathlib.Path:
    path = pathlib.Path(tempfile.mkdtemp()) / "drafts.json"
    case_store.STORE_PATH = path
    if seed:
        path.write_text(json.dumps(seed))
    return path


def rows(path):
    return json.loads(path.read_text()) if path.exists() else []


def _response(parts):
    out = []
    for kind, *rest in parts:
        if kind == "call":
            out.append(NS(function_call=NS(name=rest[0], args=rest[1]), text=None))
        else:
            out.append(NS(function_call=None, text=rest[0]))
    return NS(candidates=[NS(content=NS(parts=out))])


class FakeModel:
    """Scripted stand-in for the Gemini client. Each script item is either a
    list of ("call", name, args) / ("text", str) parts, or an Exception."""

    def __init__(self, script):
        self.script = list(script)
        self.calls = 0
        self.models = self

    def generate_content(self, model, contents, config):
        self.calls += 1
        item = self.script.pop(0) if self.script else [("text", "ok")]
        if isinstance(item, Exception):
            raise item
        return _response(item)


def run_turn(message, script, state=None):
    state = state or SessionState()
    real_client = orch.client
    orch.client = FakeModel(script)
    try:
        result = orch.run_tool_turn(state, message)
    finally:
        orch.client = real_client
    return state, result


def record(sid, passed, evidence, tools="none", stop=None):
    RESULTS[sid] = {"result": "PASS" if passed else "FAIL", "evidence": evidence, "tools": tools, "stop": stop}


def agreed_state():
    state = SessionState()
    state.case_agreed = True
    return state


GOOD = {"student_identifier": "26/U/10013", "issue_summary": "Wi-Fi fails in hostel", "category": "it_webmail_wifi"}


# ---------------------------------------------------------------- scenarios
def a04():
    path = fresh_store()
    res = handlers.create_support_case({**GOOD, "session_id": "ATTACKER-1"}, "real-session")
    stored = rows(path)[0]["session_id"]
    record("A04", stored == "real-session" and res["session_id"] == "real-session",
           f"status={res['status']}; stored session_id={stored}", "create_support_case")


def a06():
    res = orch._run_call("close_case", {"id": "x"}, agreed_state(), "close it")
    record("A06", res["status"] == "error", f"status={res['status']}: {res.get('message')}", "close_case (unregistered)")


def c04():
    path = fresh_store()
    res = handlers.create_support_case({**GOOD, "category": "admissions"}, "s")
    record("C04", res["status"] == "validation_error" and not rows(path),
           f"status={res['status']}; rows written={len(rows(path))}", "create_support_case")


def c06():
    path = fresh_store()
    res = handlers.create_support_case({**GOOD, "category": "fees_informational",
                                        "issue_summary": "Student asks staff to waive the late fee"}, "s")
    record("C06", res["status"] == "error" and not rows(path),
           f"status={res['status']}; rows written={len(rows(path))}", "create_support_case")


def c07():
    path = fresh_store()
    res = handlers.create_support_case({**GOOD, "category": "other_unclassified",
                                        "issue_summary": "Student asks for a refund of the registration fee"}, "s")
    record("C07", res["status"] == "error" and not rows(path),
           f"status={res['status']}; rows written={len(rows(path))}; routed_queue={res.get('routed_queue')}. "
           "MCP spec section 3 says fee waiver/refund language must be refused in any category.",
           "create_support_case")


def c08():
    path = fresh_store()
    res = handlers.create_support_case({**GOOD, "category": "other_unclassified",
                                        "issue_summary": "Unspecified onboarding issue"}, "s")
    record("C08", res["status"] == "validation_error",
           f"status={res['status']}; rows written={len(rows(path))}. Week 4 recommended rejecting placeholder summaries.",
           "create_support_case")


def l03():
    fresh_store()
    handlers.retrieve = lambda q, top_k=3: [{"chunk_id": "c1", "text": "t", "source_title": "Doc", "source_url": "u", "similarity": 0.8}]
    try:
        _, r = run_turn("How do I connect to Wi-Fi?",
                        [[("call", "retrieve_documents", {"query": f"q{k}"}) for k in range(4)], [("text", "Done")]])
    finally:
        handlers.retrieve = ORIG_RETRIEVE
    statuses = [s["result"]["status"] for s in r["trace"]]
    record("L03", statuses.count("ok") == 3 and statuses[-1] == "error",
           f"statuses={statuses}", "retrieve_documents x4 requested", r["stop_condition"])


def l04():
    path = fresh_store()
    bad = {"student_identifier": "26/A/1", "issue_summary": "x", "category": "registration"}
    good = {"student_identifier": "26/U/10011", "issue_summary": "x", "category": "registration"}
    _, r = run_turn("Save my case", [[("call", "create_support_case", bad), ("call", "create_support_case", bad),
                                      ("call", "create_support_case", good)], [("text", "ok")]], agreed_state())
    statuses = [s["result"]["status"] for s in r["trace"]]
    record("L04", statuses[2] == "error" and not rows(path),
           f"case-call statuses={statuses}; rows written={len(rows(path))}", "create_support_case x3 requested", r["stop_condition"])


def l05():
    fresh_store()
    handlers.retrieve = lambda q, top_k=3: [{"chunk_id": "c1", "text": "t", "source_title": "Doc", "source_url": "u", "similarity": 0.8}]
    try:
        _, r = run_turn("How do I connect to Wi-Fi?", [[("call", "retrieve_documents", {"query": "wifi"})]] * 3)
    finally:
        handlers.retrieve = ORIG_RETRIEVE
    record("L05", r["stop_condition"] == "S7" and r["iteration_count"] == 3,
           f"stop={r['stop_condition']}; iteration_count={r['iteration_count']}", "retrieve_documents x3", r["stop_condition"])


def l06():
    a, b, c = SessionState(), agreed_state(), agreed_state()
    c.active_case_id = "CASE-2026-000001"
    n = (len(orch._declarations(a)), len(orch._declarations(b)), len(orch._declarations(c)))
    record("L06", n == (1, 2, 1), f"declarations offered: not agreed={n[0]}, agreed={n[1]}, agreed with draft={n[2]}")


def r01():
    res = handlers.retrieve_documents({"query": "   "})
    record("R01", res["status"] == "error" and res.get("message") == "query is required",
           f"status={res['status']}; message={res.get('message')}; chunks={res['retrieved_count']}", "retrieve_documents")


def r02():
    def boom(q, top_k=3):
        raise RuntimeError("index missing")
    handlers.retrieve = boom
    try:
        res = handlers.retrieve_documents({"query": "wifi"})
    finally:
        handlers.retrieve = ORIG_RETRIEVE
    record("R02", res["status"] == "error" and res["retrieved_count"] == 0,
           f"status={res['status']}; message={res.get('message')}; chunks={res['retrieved_count']}", "retrieve_documents")


def r03():
    handlers.retrieve = lambda q, top_k=3: [{"chunk_id": "c9", "text": "t", "source_title": "Doc", "source_url": "", "similarity": 0.9}]
    try:
        res = handlers.retrieve_documents({"query": "wifi"})
    finally:
        handlers.retrieve = ORIG_RETRIEVE
    record("R03", res["status"] == "no_match", f"status={res['status']}; chunks={res['retrieved_count']}", "retrieve_documents")


def r04():
    fresh_store()
    state, r = run_turn("How do I activate webmail?", [RuntimeError("503 UNAVAILABLE: model overloaded")])
    raw = "503" in r["text"] or "UNAVAILABLE" in r["text"]
    record("R04", not raw, f"student-facing text: '{r['text']}'. The raw exception text is shown to the student."
           if raw else f"student-facing text: '{r['text']}'", "none", r["stop_condition"])


def r05():
    path = fresh_store()
    state = agreed_state()
    _, r = run_turn("Save my case", [[("call", "create_support_case", GOOD)], RuntimeError("503 UNAVAILABLE")], state)
    ok = "CASE-" in r["text"] and r["stop_condition"] == "S2" and len(rows(path)) == 1
    record("R05", ok, f"stop={r['stop_condition']}; reply: {r['text'][:160]}; rows={len(rows(path))}",
           "create_support_case", r["stop_condition"])
    return state, path


def r06(state, path):
    _, r = run_turn("Please create the case again", [[("call", "create_support_case", GOOD)], [("text", "ok")]], state)
    statuses = [s["result"]["status"] for s in r["trace"]]
    record("R06", statuses == ["error"] and len(rows(path)) == 1,
           f"second attempt statuses={statuses}; rows={len(rows(path))}; active_case_id={state.active_case_id}",
           "create_support_case")


def main():
    for fn in (a04, a06, c04, c06, c07, c08, l03, l04, l05, l06, r01, r02, r03, r04):
        fn()
    state, path = r05()
    r06(state, path)
    order = ["A04", "A06", "C04", "C06", "C07", "C08", "L03", "L04", "L05", "L06", "R01", "R02", "R03", "R04", "R05", "R06"]
    for sid in order:
        r = RESULTS[sid]
        print(f"{sid}  {r['result']:4}  {r['evidence'][:140]}")
    passed = sum(1 for s in order if RESULTS[s]["result"] == "PASS")
    print(f"\n{passed} PASS, {len(order) - passed} FAIL out of {len(order)}")
    pathlib.Path("deterministic_results.json").write_text(json.dumps(RESULTS, indent=2), encoding="utf-8")
    print("wrote deterministic_results.json")


if __name__ == "__main__":
    main()
