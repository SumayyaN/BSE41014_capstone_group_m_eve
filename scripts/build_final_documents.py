"""Build the Week 8 hand-in PDFs and the presentation outside the repository."""
from pathlib import Path

from fpdf import FPDF
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.util import Inches, Pt

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
EVAL = DOCS / "evaluation"
REPORTS = DOCS / "weekly-reports"
TIMES = r"C:\Windows\Fonts\times.ttf"
TIMES_B = r"C:\Windows\Fonts\timesbd.ttf"
TIMES_I = r"C:\Windows\Fonts\timesi.ttf"
SLIDES = Path(r"C:\Users\aryam\Downloads\Group_M_eve_Final_Presentation.pptx")

MAROON = RGBColor(0x7A, 0x00, 0x19)
GOLD = RGBColor(0xC4, 0xA3, 0x5A)
INK = RGBColor(0x1F, 0x1A, 0x17)
SLATE = RGBColor(0x3E, 0x46, 0x4C)
CREAM = RGBColor(0xF7, 0xF3, 0xEC)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)


class Handout(FPDF):
    def __init__(self, running_title: str, body: int = 11, leading: float = 5.4):
        super().__init__(format="A4")
        self.running_title = running_title
        self.body = body
        self.leading = leading
        self.set_auto_page_break(auto=True, margin=18)
        self.set_margins(20, 18, 20)
        self.add_font("TNR", "", TIMES)
        self.add_font("TNR", "B", TIMES_B)
        self.add_font("TNR", "I", TIMES_I)

    def header(self):
        if self.page_no() == 1:
            return
        self.set_font("TNR", "I", 9)
        self.set_text_color(40, 40, 40)
        self.cell(0, 6, self.running_title, new_x="LMARGIN", new_y="NEXT")
        self.line(20, 16, 190, 16)
        self.ln(3)

    def footer(self):
        self.set_y(-14)
        self.set_font("TNR", "", 9)
        self.set_text_color(40, 40, 40)
        self.cell(0, 8, str(self.page_no()), align="C")

    def h1(self, text: str):
        self.ln(2)
        self.set_font("TNR", "B", 14)
        self.set_text_color(0, 0, 0)
        self.multi_cell(0, 7, text, new_x="LMARGIN", new_y="NEXT")
        self.ln(1)

    def h2(self, text: str):
        self.ln(1)
        self.set_font("TNR", "B", 12)
        self.multi_cell(0, 6, text, new_x="LMARGIN", new_y="NEXT")
        self.ln(0.5)

    def p(self, text: str):
        self.set_font("TNR", "", self.body)
        self.multi_cell(0, self.leading, text, align="L", new_x="LMARGIN", new_y="NEXT")
        self.ln(1.6)

    def bullet(self, text: str):
        self.set_font("TNR", "", self.body)
        self.multi_cell(0, self.leading, "- " + text, align="L", new_x="LMARGIN", new_y="NEXT")
        self.ln(0.6)


def save(pdf: FPDF, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(path))
    print("wrote", path)


def engineering_report() -> Handout:
    pdf = Handout("BSE4104 Group M Evening | Final Engineering Report", body=12, leading=6.4)
    pdf.add_page()
    pdf.set_font("TNR", "B", 16)
    pdf.multi_cell(0, 8, "University Student-Support Case Agent", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("TNR", "B", 13)
    pdf.multi_cell(0, 7, "Final Engineering Report", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)
    pdf.set_font("TNR", "", 11)
    pdf.multi_cell(
        0,
        5.4,
        "BSE4104 AI Agentic Systems Capstone\n"
        "Group M Evening, Makerere University\n"
        "Namata Sumayya (23/U/22615), Nakaye Hildah (23/U/13598/PS),\n"
        "Mushabe Moses (23/U/12131/EVE), Aryampa Joshua (23/U/06517/PS)\n"
        "Course convener: Dr Kamulegeya Grace B\n"
        "Final release: git tag v1.5.0 on branch week8-release\n"
        "23 October 2026",
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.ln(2)

    pdf.h1("1. Executive Summary")
    pdf.p(
        "New Makerere University students need a reliable way to complete the first "
        "onboarding steps: webmail, campus Wi-Fi, the ACMIS portal, and registration. "
        "The public instructions exist, but they are spread across several documents. "
        "A general chat model can sound confident while inventing a step that is not "
        "in those documents. The group built a bounded support agent for freshman "
        "onboarding only. It answers from an approved corpus, cites the source, and, "
        "when the student agrees, saves one support draft for a staff queue. It does "
        "not decide admissions, grades, discipline, or fees."
    )
    pdf.p(
        "The system uses gemini-3.6-flash for answers and gemini-embedding-001 for "
        "retrieval. Two tools are available: retrieve_documents and create_support_case. "
        "The application, not the model, executes tools and enforces a three-round "
        "limit, a three-tool-call limit, and one draft per session. Week 3 retrieval "
        "passed 11 of 15 questions (73%). Week 7 passed 29 of 36 scenarios (80.5%). "
        "Week 8 fixed five defects from that evaluation. The principal remaining "
        "limit is retrieval: some relevant fee and joining passages still score below "
        "the 0.70 similarity cutoff, so the agent refuses rather than guess."
    )

    pdf.h1("2. Problem Context and Requirements")
    pdf.p(
        "The user is a freshman who is trying to activate an account or follow a "
        "published onboarding step. The workflow is short. The student asks a question. "
        "The agent searches the approved documents. If a passage is relevant, the "
        "answer is grounded in it and the source title is shown. If nothing relevant "
        "is found, the agent says so and may offer a support draft. The student must "
        "click \"I agree to save a support draft\" before a draft can be written. "
        "Staff still own the case. The agent cannot resolve, close, or reassign it."
    )
    pdf.p(
        "The requirements are recorded in the Agent Task Contract, the user stories "
        "and acceptance criteria, and the prompt specification. Success means a "
        "grounded answer with a source, a correct refusal when the question is outside "
        "freshman onboarding, or a validated draft in the right queue. A wrong success "
        "is an invented procedure, a fee or grade decision, a draft saved without "
        "agreement, or a second draft in the same session."
    )
    pdf.p(
        "The AI boundary is deliberate. The model may draft language and choose a "
        "tool. It may not change a university record, approve a refund, alter a grade, "
        "or speak for admissions or a disciplinary body. High-impact actions stay "
        "with a person. The corpus is public university guidance plus the group's "
        "controlled copies. The agent does not connect to ACMIS, the fees ledger, or "
        "any live student database."
    )
    pdf.p(
        "Acceptance is checked against behaviour, not against a pleasant tone. A "
        "webmail question passes when the reply follows a retrieved passage and names "
        "the source. A continuing student passes when the reply refuses and does not "
        "search. A draft passes when the sidebar agreement is on, the summary is a "
        "real sentence, the registration number matches the freshman pattern, and "
        "the stored row has a queue. It fails when any of those is missing, when a "
        "second draft is written in the same session, or when the summary asks for "
        "a waiver or a refund. These checks are the acceptance criteria the Week 7 "
        "scenarios and the deterministic script both use."
    )

    pdf.h1("3. System Architecture")
    pdf.p(
        "The running application is a Streamlit page, src/app.py. The student picks "
        "a prompt version in the sidebar. Versions v1.0 and v1.1 call the model with "
        "no documents. Version v1.2 adds retrieval. Version v1.3 is the agent. For "
        "v1.3 the page calls run_tool_turn in src/tools/orchestrate.py. Session data "
        "lives in SessionState: session id, conversation, agreement flag, active case "
        "id, retrieved context, iteration count, and the tool log."
    )
    pdf.p(
        "Deterministic code surrounds the model. Before any model call, Sense checks "
        "the current student message for an instruction-override attempt (stop S6), "
        "a statement that the student is not a freshman (stop S4), and a blocked "
        "decision topic (stop S5). Only a message that passes those checks is sent "
        "to Gemini, together with the tool declarations. If the model requests a "
        "tool, handlers.py runs retrieve_documents or create_support_case. The model "
        "never writes the draft file itself."
    )
    pdf.p(
        "Retrieval is local. Chunks and embeddings are files under data/chunks/. "
        "Drafts are a JSON file under data/cases/, which is not committed. Each v1.3 "
        "turn also writes one JSON log under logs/, which is not committed. Sample "
        "logs are kept in evidence/traces/. The external dependency is the Gemini "
        "API, reached with a key in .env. There is no other network tool, browser, "
        "or payment integration."
    )
    pdf.p(
        "The boundary between components is the reason the system can be tested "
        "without a live model. Sense, validation, and the draft store are ordinary "
        "Python. The deterministic suite substitutes a fake Gemini client and a "
        "temporary draft file. That is how C07, C08, R04, and the limit checks can "
        "fail or pass on a machine with no API key. The model boundary is also where "
        "a 503 stops. The orchestration layer catches it, writes the raw text into "
        "the turn log, and returns a short sentence to the page. The student never "
        "has to interpret an HTTP status."
    )

    pdf.h1("4. Foundation Model and Prompt Engineering")
    pdf.p(
        "The group selected Gemini because the course work needed both a chat model "
        "and an embedding model from one provider, with a free-tier key that every "
        "member could use. The answer model in the release is gemini-3.6-flash. "
        "Embeddings use gemini-embedding-001. The choice is an engineering trade-off, "
        "not a claim that this model is the best general assistant. It is small "
        "enough to call from a student project, and the application treats its output "
        "as untrusted until the tools and checks have run."
    )
    pdf.p(
        "Prompts are files, not strings hidden in the interface. prompts/v1.0_baseline.txt "
        "is an unconstrained baseline. v1.1 limits the role to freshman onboarding. "
        "v1.2 requires answers from retrieved passages and a refusal when retrieval "
        "is empty. v1.3 adds the two tools, the agreement rule, and the draft rules. "
        "load_prompt reads the version the sidebar selects. The Week 7 and Week 8 "
        "release run v1.3."
    )
    pdf.p(
        "The important iteration was to stop asking the model to be the safety system. "
        "Early prompts said the assistant must not decide fees or grades. That sentence "
        "is still in the prompt, but the release also blocks those topics in code "
        "before the model is called, and it rejects fee-decision language inside "
        "create_support_case no matter which category the model picked. Prompt text "
        "is guidance. The stop conditions are the control."
    )

    pdf.h1("5. Context Engineering and RAG")
    pdf.p(
        "The corpus is eight public Makerere freshman-onboarding documents, listed in "
        "the corpus source register. The pipeline is download_sources.py, "
        "extract_text.py, chunk_text.py, and embed_chunks.py. Chunks are about 1,500 "
        "characters. The Week 3 index held 90 chunks. chunks.json is committed so the "
        "text can be inspected. The embedding file is not committed, because it is "
        "large and can be rebuilt. The live timetable site is excluded. It is not a "
        "stable document."
    )
    pdf.p(
        "retrieve.py ranks chunks by cosine similarity and returns at most three "
        "chunks at or above 0.70. The threshold was chosen after comparing 0.50, "
        "0.65, and 0.70 on the Week 3 questions. A lower bar returned more passages "
        "and also more weak matches. The agent would rather say that it did not find "
        "a source than quote a weak one."
    )
    pdf.p(
        "Week 3 scored 11 of 15 (73%). Answerable questions passed 4 of 5. Unanswerable "
        "questions passed 5 of 5, which means the refusal path worked when the corpus "
        "did not contain the answer. The misses were mostly threshold misses: joining "
        "instructions, Eduroam troubleshooting, webmail password reset, and a combined "
        "Wi-Fi question. Week 7 scenario I02 is the same class of miss. A question "
        "about whether functional fees are refundable did not clear 0.70, so the "
        "agent refused. Week 8 did not lower the threshold and did not add a keyword "
        "index. Either change would need the 15-question set, and the full scenario "
        "set, to be scored again."
    )
    pdf.p(
        "Grounding is a rule in the reply, not only in the retriever. When status "
        "is ok, the answer is supposed to follow the passages and name the source. "
        "When status is no_match, the answer must not fill the gap from general "
        "knowledge about universities. The stop for that path is S3. The student "
        "can still be offered a draft, and that draft records the question. It does "
        "not record an answer the documents did not support. This is why a retrieval "
        "miss is classified as a remaining limit rather than as a silent success. "
        "The student is told the document was not found. A staff member can still "
        "answer the fee question from the policy itself."
    )

    pdf.h1("6. Tools and Agentic Workflow")
    pdf.p(
        "retrieve_documents takes a query and returns status, a count, and source "
        "titles with similarity. It does not return the whole corpus to the student. "
        "create_support_case takes a category, an issue summary, and the student "
        "registration number when one was given. It validates the registration number "
        "against the freshman pattern, rejects an empty or placeholder summary, and "
        "rejects any summary that asks to waive, refund, or approve a fee. Valid "
        "drafts are stored locally with an id of the form CASE-year-six digits and "
        "a queue: webmail and Wi-Fi to the ICT helpdesk, registration to the "
        "registration office, fee information to fees information, accommodation to "
        "the accommodation office, and anything else to general onboarding."
    )
    pdf.p(
        "The loop is Sense, Plan, Act, Observe, Stop. Sense is the code checks above. "
        "Plan is the model, which may request a tool. Act is the handler. Observe "
        "feeds the tool result back for another round. Stop ends the turn with one "
        "of eight labels. S1 is a grounded answer. S2 is a saved draft and the hand-off "
        "to staff. S3 is no matching document, with an offer to draft a case. S4 is "
        "out of freshman scope. S5 is a blocked topic. S6 is an instruction-override "
        "attempt. S7 is the three-round limit. S8 is a tool error after one retry."
    )
    pdf.p(
        "Limits are constants in orchestrate.py: three rounds, three tool calls per "
        "turn, two case calls per turn so one validation error can be corrected, and "
        "one successful draft per session. A second create for the same registration "
        "number is refused by the case history check. The agreement control is the "
        "sidebar button. Typing \"I agree\" in the chat is not enough, because the "
        "flag is set only by that button. Week 5 traces T1, T2, and T3 show a grounded "
        "answer, a draft, and a failure recovery under these rules."
    )
    pdf.p(
        "A registration number is accepted only when it matches the freshman form "
        "used in the case store: two digits, a slash, U or X, a slash, four or five "
        "digits, and an optional /PS or /EVE suffix. The number is read from the "
        "student's own messages when the draft is tied to a person. The model is "
        "not allowed to invent one. Queues are a fixed map, not a free-text field. "
        "Webmail and Wi-Fi go to the ICT helpdesk. Registration goes to the "
        "registration office. A fees information question goes to fees information. "
        "Accommodation goes to the accommodation office. Anything else goes to "
        "general onboarding. The queue is a label for a person. It is not a dispatch "
        "into a live helpdesk system."
    )

    pdf.h1("7. Memory, State and Interoperability")
    pdf.p(
        "Two stores are easy to confuse, and the design keeps them apart. Session "
        "state lasts while the Streamlit session lasts. A reload clears the "
        "conversation, the agreement flag, and the active case id. The draft file "
        "on disk does not clear. That split is intentional. The chat is temporary. "
        "The staff draft is the record."
    )
    pdf.p(
        "Persistent memory is Case History Recall, not a vector memory of the chat. "
        "If the current student message asks about a prior case, the registration "
        "number is taken only from the student's own messages, not from the "
        "assistant's text. get_case_history reads drafts.json by that exact "
        "identifier and injects a note for the rest of the turn. The group did not "
        "implement a 90-day deletion job. Drafts stay until a person removes the "
        "local file. The memory note records that limit. Drafts are gitignored so "
        "a registration number is not pushed to GitHub."
    )
    pdf.p(
        "The interoperability artefact is an MCP-style interface specification for "
        "create_support_case, not a live Model Context Protocol server. The course "
        "reading did not cover MCP in the supplied editions, and the assignment "
        "allowed a clear interface design. The specification states the inputs, the "
        "validation errors, the queues, and the actions the tool will not perform. "
        "A later team could wrap the same handler as an MCP tool without changing "
        "the safety checks."
    )

    pdf.h1("8. Evaluation, Observability and Guardrails")
    pdf.h2("8.1 What was measured")
    pdf.p(
        "Week 3 measured retrieval and grounded answers on 15 questions: answerable, "
        "partly answerable, and unanswerable. Week 7 measured the full agent on 36 "
        "scenarios, above the 30-scenario minimum. A scenario passed only when every "
        "applicable criterion passed: task completion, groundedness, tool choice, "
        "scope, latency under a 10-second target, and safety. The set mixes live "
        "Gemini calls and deterministic checks that use a fake client, so the safety "
        "paths do not depend on the model having a good day."
    )
    pdf.h2("8.2 Results")
    pdf.p(
        "Week 3: 11/15 (73%). Week 7: 29/36 (80.5%). Normal grounded questions and "
        "the adversarial injection cases passed. Limit checks passed, including the "
        "three-round stop. Incorrect-information cases passed at 80% because I02 "
        "missed the fee passage. Blocked-topic cases passed at 75% because two "
        "information questions were over-refused. Edge cases passed at 50% because "
        "a second-year student was treated as a freshman and a raw API error was "
        "shown in the chat. Latency sometimes exceeded 10 seconds: 13.6 seconds on "
        "a memory lookup and 12.5 seconds on case creation. Those turns still "
        "completed. The 10-second figure is a target, not a hard stop."
    )
    pdf.h2("8.3 Guardrails")
    pdf.p(
        "The guardrails are the Sense stops, the tool allow-list, schema validation, "
        "the agreement flag, the draft caps, and the rule that resolve, close, and "
        "reassign are not registered tools. Prompt injection is refused before tools "
        "run. A caller cannot supply a different session id and have it trusted. "
        "Fee-decision wording is rejected in the summary. The observability evidence "
        "and the guardrail evidence PDFs record these checks. Each v1.3 turn writes "
        "one log with the turn id, session id, latency, model and round count, prompt "
        "id, whether a case-history note was used, the student message, retrieval "
        "status and source titles, tool names and shortened results, the error if "
        "any, the stop condition, and a reply preview of at most 400 characters. "
        "Passage bodies and the full prompt are not stored."
    )
    pdf.h2("8.4 Week 8 remediation and retest")
    pdf.p(
        "Five failures were code defects and were fixed on tag v1.5.0. Information "
        "questions about the Code of Conduct or an admission letter are no longer "
        "blocked, while a request for admissions help or a grade change still stops "
        "at S5. A 503 or 429 is shown as \"The assistant is temporarily busy. Please "
        "try again in a few minutes.\" The raw error remains in the log. If a draft "
        "was already saved, the reply still includes the case id and stops at S2. "
        "Second-year, third-year, fourth-year, fifth-year, and 2nd-year through "
        "5th-year phrasing now stop at S4. Placeholder summaries, including "
        "\"Unspecified onboarding issue\" and summaries shorter than 8 characters, "
        "are validation errors. Fee-decision language is rejected in every category."
    )
    pdf.p(
        "python run_deterministic_checks.py from src/ passed 16 of 16, including "
        "C07, C08, R04, and R05, which had encoded the expected behaviour and were "
        "failing before the fix. python week8_retest.py passed 5 of 5 on the code "
        "checks: the Code of Conduct question and the admission-letter question are "
        "not blocked, while an admissions decision, a grade change, and the "
        "second-year sentence still stop before the model. Those results are in "
        "docs/evaluation/week8_retest.json."
    )
    pdf.p(
        "On 24 October 2026 the 19 live chats were run again from "
        "docs/evaluation/week8_runner_input.xlsx. The committed Week 7 results file "
        "has 35 scenarios, not the 36 named in the Week 7 write-up. The 29/36 figure "
        "is not rewritten. Eighteen chats finished. B07 now cites the Joining "
        "Instructions and lists the registration documents, stop S1. N03 now stops "
        "at S4 with no model call. I02 still returns no_match and stops at S3. B06 "
        "is no longer blocked in code, but the model refuses it and does not search, "
        "so the grounded-answer criterion still fails. M01, the memory question, "
        "stopped because Gemini returned 429 after the free-tier quota was used up. "
        "That turn is not scored as a product failure. Replies are in "
        "docs/evaluation/week8_live_results.csv. C05 saved one fees draft, "
        "CASE-2026-000001, in 11.4 seconds."
    )
    pdf.p(
        "The checked-in traces are the inspection path when a marker cannot run "
        "Gemini. T1 is a grounded answer. T2 is a draft. T3 is a failure that "
        "recovers inside the limits. O1 is the admissions refusal at S5, with no "
        "model call. O2 is an instruction-override refusal at S6. O3 is a grounded "
        "webmail retrieval. During that run the model returned 503, so O3 records "
        "the retrieval result and says the model was unavailable. O4 keeps the live "
        "503, including a latency of 8334 milliseconds, in the log rather than in "
        "the chat. Together they show a success, a hand-off, a blocked topic, an "
        "attack refused before tools, and a dependency failure that the application "
        "can name."
    )

    pdf.h1("9. Software Engineering Quality and Deployment")
    pdf.p(
        "The repository is https://github.com/SumayyaN/BSE41014_capstone_group_m_eve. "
        "History is on main through the Week 7 seal. The final release is annotated "
        "tag v1.5.0 on branch week8-release. Tag v1.3.0 is the Week 7 snapshot. Tag "
        "v1.4.0 is the README release before these defect fixes. A marker should "
        "check out v1.5.0. Run instructions are in the README: Python 3.11 or newer, "
        "pip install -r requirements.txt, a GEMINI_API_KEY in .env copied from "
        ".env.example, the four RAG scripts, then python -m streamlit run src/app.py "
        "from the repository root."
    )
    pdf.p(
        "Secrets stay out of git. .env is ignored. The sample file contains the "
        "variable name only. Drafts, embeddings, raw downloads, and logs are ignored. "
        "The checked-in traces are the Week 5 T1-T3 samples and the Week 7 O1-O4 "
        "samples. There is no continuous-integration workflow in the repository. "
        "The tests that travel with the release are the deterministic script and the "
        "Week 8 retest script. They do not need an API key. The live scenario runner "
        "does. The group did not deploy a public server. The reproducible run is the "
        "local Streamlit application from the tag. That matches the assignment option "
        "of a deployed or reproducibly runnable release."
    )
    pdf.p(
        "Code review happened through pull requests on the shared repository, "
        "including the bounded-agent workflow, the memory work, and the observability "
        "logs. Week 8 fixes are small and sit next to the tests that name the old "
        "failures. A later maintainer can change a queue or a stop message without "
        "rewriting the model prompt, because those rules are tables and constants."
    )
    pdf.p(
        "Reproducibility was treated as a deliverable, not as a hope. The README "
        "names tag v1.5.0, the Python version, the install command, the order of "
        "the four corpus scripts, and the Streamlit command. chunks.json is in git "
        "so the text of the corpus can be read before embeddings are rebuilt. The "
        "embedding file, raw downloads, drafts, and logs are generated on the "
        "machine that runs the demo. A second machine with the same key and the "
        "same tag should reach the same sidebar, the same two tools, and the same "
        "stop ids. It may not reach the same latency. The free-tier Gemini service "
        "has already returned 503 when demand was high, and a 429 when the daily "
        "embedding quota was exhausted. The embed script resumes after a 429. The "
        "chat path now explains a 503 without pasting it."
    )
    pdf.p(
        "Maintainability also means a marker can see the limit without reading the "
        "chat code. STOP_CONDITIONS in orchestrate.py is the list S1 to S8. The "
        "failure catalogue names the six Week 7 misses and says which five were "
        "repaired. The README lists the two limits that remain: the 0.70 miss, and "
        "turns that can run past 10 seconds. A change to a queue name or a blocked "
        "phrase should be followed by the deterministic script. That script is the "
        "regression check for this release. It is not a substitute for a later live "
        "run, and the report does not pretend that it is."
    )

    pdf.h1("10. Results, Limitations and Professional Reflection")
    pdf.p(
        "What works is the path the product was built for. A freshman can ask how to "
        "activate webmail, see a cited answer when the passage clears 0.70, and, "
        "after an explicit click, leave one draft for staff. Injection attempts, "
        "grade changes, fee decisions, and non-freshman users are refused by code. "
        "A reader can inspect a turn log and see which stop fired and which tool ran."
    )
    pdf.p(
        "What does not work yet is complete recall of the corpus. Similarity at 0.70 "
        "misses some passages a person would judge relevant, especially fee policy "
        "and a few joining-instruction details. The safe response is a refusal, and "
        "that refusal can be wrong from the student's point of view. Latency can "
        "exceed 10 seconds when the model is slow or returns 503 under load. The "
        "student now sees a short retry message, but the answer is still delayed. "
        "There is no staff inbox, no authentication, and no deletion schedule for "
        "drafts. Those are product limits, not hidden features."
    )
    pdf.p(
        "The professional point is that the model is not the system of record. A "
        "support answer that affects a fee, a place, or a case status has to be "
        "owned by a member of staff. The agent prepares a draft and shows its "
        "evidence. It does not close the case. Future work, if the university "
        "authorised it, would be a staff review screen, a retention period for "
        "drafts, and a retrieval evaluation before any change to the 0.70 cutoff. "
        "Until that evaluation exists, the cutoff stays."
    )
    pdf.p(
        "Cost and latency belong in the same reflection. The project uses the "
        "Gemini free tier. There is no separate budget line and no paid deployment. "
        "A grounded turn is one embedding comparison locally plus one or two "
        "generate calls. Week 7 saw turns above the 10-second target, up to 13.6 "
        "seconds. That is acceptable for a demonstration and poor for a busy "
        "helpdesk. The response in this release is honesty in the log and a calm "
        "sentence in the chat, not a claim that the free tier is a production "
        "service. If the university later hosted this agent, the first work would "
        "be a staff queue with names on it, an authentication boundary, a retention "
        "rule for drafts, and a fresh retrieval score before anyone moved 0.70."
    )
    pdf.p(
        "The demonstration should make the same distinction the report makes. A "
        "successful webmail answer shows the cited source. A turn log shows the "
        "retrieval count, the tool, and the stop id. The fee-refund question shows "
        "the remaining retrieval miss, or the second-year sentence shows the scope "
        "refusal that Week 8 closed. The agreement button shows the human gate. "
        "None of those moments require the agent to be trusted on tone. Each one "
        "can be checked against a file or a stop id."
    )

    pdf.h1("References")
    pdf.p(
        "Huyen, C. (2025). AI Engineering: Building Applications with Foundation "
        "Models. O'Reilly Media."
    )
    pdf.p(
        "Lanham, M. (2025). AI Agents in Action. Manning Publications."
    )
    pdf.p(
        "Osmani, A. (2025). Beyond Vibe Coding: From Coder to AI-Era Developer. "
        "O'Reilly Media."
    )
    pdf.p(
        "Group M Evening. (2026). Repository evidence cited in the appendix: Agent "
        "Task Contract, prompt specification, tool catalogue, corpus source register, "
        "memory note, MCP-style interface specification, Week 3 rag_eval.md, Week 7 "
        "evaluation report, failure catalogue, and observability samples. Makerere "
        "University, BSE4104. https://github.com/SumayyaN/BSE41014_capstone_group_m_eve"
    )

    pdf.h1("Appendix A. Evidence index")
    pdf.p(
        "This appendix is outside the 8-12 page body. It points at files in tag v1.5.0."
    )
    for line in [
        "docs/requirements/Agent Task Contract M EVE.pdf",
        "docs/requirements/Group_M_User_Stories_and_Acceptance_Criteria.pdf",
        "docs/requirements/Group M - Prompt Specification v1.0.pdf",
        "docs/requirements/Tool_Catalogue_and_API_Schemas.pdf",
        "docs/requirements/Group M - Corpus Source Register.pdf",
        "docs/requirements/Memory_Design_and_Data_Handling_Note.pdf",
        "docs/requirements/MCP_Interface_Specification create_support_case.pdf",
        "docs/Architecture/Group_M_eve_State_Model.pdf",
        "docs/evaluation/rag_eval.md",
        "docs/evaluation/week7_evaluation.md",
        "docs/evaluation/failure_catalogue_week7.md",
        "docs/evaluation/week8_retest.json",
        "docs/evaluation/week8_live_results.csv",
        "docs/evaluation/week8_runner_input.xlsx",
        "docs/evaluation/Group_M_eve_Observability_Tracing_Evidence.pdf",
        "docs/evaluation/guardrail_Implementation_Evidence.pdf",
        "docs/evaluation/Group_M_eve_Final_Evidence_Pack.pdf",
        "evidence/traces/T1_grounded_answer.json, T2_case_draft.json, T3_failure_recovery.json",
        "evidence/traces/O1_blocked_topic.json through O4_model_unavailable.json",
        "src/run_deterministic_checks.py and src/week8_retest.py",
    ]:
        pdf.bullet(line)

    pdf.h1("Appendix B. Week 8 retest")
    pdf.p(
        "Deterministic suite after the fixes: 16 PASS, 0 FAIL. The code retest lets "
        "B06 and B07 through and still blocks an admissions decision, a grade change, "
        "and a second-year sentence. The 24 October live run confirms B07 and N03. "
        "I02 still misses at 0.70. B06 is refused by the model. M01 did not finish "
        "because the Gemini quota returned 429."
    )
    return pdf


def evidence_pack() -> Handout:
    pdf = Handout("BSE4104 Group M Evening | Final Evidence Pack")
    pdf.add_page()
    pdf.set_font("TNR", "B", 16)
    pdf.multi_cell(0, 8, "Final Evaluation and Evidence Pack", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("TNR", "", 11)
    pdf.multi_cell(
        0,
        5.4,
        "University Student-Support Case Agent\n"
        "Group M Evening | BSE4104 | 23 October 2026\n"
        "Release tag v1.5.0",
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.ln(2)
    pdf.h1("1. How to read this pack")
    pdf.p(
        "This pack is the index for the evaluation evidence. The detailed numbers "
        "stay in the files they were first recorded in. Week 7 totals are not "
        "rewritten after the Week 8 fixes. A reader who wants the original score "
        "uses week7_evaluation.md. A reader who wants the repair uses the failure "
        "catalogue and week8_retest.json."
    )
    pdf.h1("2. Evidence map")
    rows = [
        ("Foundation model", "gemini-3.6-flash in src/tools/orchestrate.py and src/llm_client.py. Rationale in the model selection note."),
        ("Prompts", "prompts/v1.0_baseline.txt through prompts/v1.3_tools.txt, plus the prompt specification PDF."),
        ("RAG", "Corpus register, data/chunks/chunks.json, src/rag/retrieve.py, docs/evaluation/rag_eval.md. Result: 11/15 (73%)."),
        ("Tools", "retrieve_documents and create_support_case. Tool catalogue PDF and the MCP-style specification."),
        ("Bounded agent", "src/tools/orchestrate.py. Stops S1-S8. Traces evidence/traces/T1, T2, and T3."),
        ("State and memory", "src/agent/state.py, Case History Recall, state-model PDF, memory note."),
        ("Evaluation", "36 scenarios, 29/36 (80.5%). week7_evaluation.md and the scenario workbook."),
        ("Observability", "src/observability/turn_log.py. Samples O1-O4. Observability PDF."),
        ("Guardrails", "Sense stops, validation, agreement flag, tool allow-list. Guardrail evidence PDF."),
        ("Week 8 retest", "16/16 deterministic checks. 5/5 scope checks. Failure 6 left open."),
    ]
    for title, body in rows:
        pdf.h2(title)
        pdf.p(body)

    pdf.h1("3. Week 8 retest record")
    pdf.p(
        "Command, from src/, with no API key: python run_deterministic_checks.py. "
        "Result: 16 PASS, 0 FAIL. The checks that had been failing on the Week 7 "
        "code were C07 (fee decision under a non-fee category), C08 (placeholder "
        "summary), and R04 (raw 503 text). R05 still expects the case id to be "
        "named when a draft was saved before the model error. That check passed."
    )
    pdf.p(
        "Command: python week8_retest.py. Result: 5 PASS, 0 FAIL. B06, the Code of "
        "Conduct question, is not blocked. B07, the admission-letter documents "
        "question, is not blocked. \"I need help with admissions for next year\" is "
        "still blocked. \"Please change my grade\" is still blocked. \"I'm a "
        "second-year student and need the Wi-Fi password.\" is still out of scope."
    )
    pdf.h1("4. Live retest on 24 October 2026")
    pdf.p(
        "Nineteen live chats were run from docs/evaluation/week8_runner_input.xlsx. "
        "Eighteen finished. The replies are in docs/evaluation/week8_live_results.csv. "
        "B07 passes with a cited list of registration documents. N03 stops at S4. "
        "I02 still returns no_match and stops at S3. B06 reaches the model, which "
        "refuses the Code of Conduct question without searching. M01 did not finish: "
        "Gemini returned 429 RESOURCE_EXHAUSTED. The Week 7 score of 29/36 is not "
        "rewritten. The results file used for this run has 35 rows."
    )
    pdf.p(
        "During Week 7 observability, gemini-3.6-flash returned 503 under load. O4 "
        "stores that 503. The student-facing path for the same class of error is "
        "now the short busy message, which R04 checks without calling the network. "
        "The live runner treats that busy sentence as an infrastructure error and "
        "retries it. M01 still exhausted the free-tier quota after those retries."
    )
    pdf.p(
        "I02 and Week 3 Q5 remain retrieval misses at the 0.70 cutoff. No new "
        "similarity number is claimed for them in Week 8, because the index was "
        "not rebuilt and the questions were not re-embedded."
    )
    pdf.h1("5. Reproduce")
    pdf.bullet("git checkout v1.5.0")
    pdf.bullet("pip install -r requirements.txt")
    pdf.bullet("Copy .env.example to .env and set GEMINI_API_KEY for any live run.")
    pdf.bullet("From src/rag/: download_sources.py, extract_text.py, chunk_text.py, embed_chunks.py.")
    pdf.bullet("From the repo root: python -m streamlit run src/app.py")
    pdf.bullet("From src/: python run_deterministic_checks.py")
    pdf.bullet("From src/: python week8_retest.py")
    pdf.bullet("Live chats, uses quota: python run_scenarios.py ../docs/evaluation/week8_runner_input.xlsx --repeat 1")
    return pdf


def progress_report() -> Handout:
    pdf = Handout("BSE4104 Group M Evening | Week 8 Progress Report")
    pdf.add_page()
    pdf.set_font("TNR", "B", 16)
    pdf.multi_cell(0, 7, "Week 8 Progress Report", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("TNR", "", 11)
    pdf.multi_cell(
        0,
        5.2,
        "BSE4104 AI Agentic Systems\n"
        "University Student-Support Case Agent\n"
        "Group M Evening\n"
        "Week ending 23 October 2026",
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.ln(1)
    pdf.h1("Work completed")
    pdf.p(
        "Week 8 was hardening, the final release, and the demonstration pack. "
        "The README run instructions and tag v1.4.0 were already in the repository. "
        "This week closed the five code defects from the Week 7 failure catalogue, "
        "retested them, wrote the final engineering report and this evidence pack, "
        "and prepared the presentation outside the repository."
    )
    for line in [
        "Fixed the raw 503 reply, second-year scope, placeholder summaries, and fee-decision text in every category. Information questions are no longer blocked in code.",
        "Scripted retest: 16/16 deterministic checks and 5/5 code checks. Recorded in docs/evaluation/week8_retest.json.",
        "Live retest, 24 October 2026: 18 of 19 chats finished. B07 and N03 pass. I02 still misses. B06 is refused by the model. M01 stopped on Gemini quota 429. Results: docs/evaluation/week8_live_results.csv.",
        "Final engineering report: docs/Group_M_eve_Final_Engineering_Report.pdf.",
        "Evidence pack: docs/evaluation/Group_M_eve_Final_Evidence_Pack.pdf.",
        "Release tag v1.5.0 on branch week8-release. v1.3.0 remains the Week 7 snapshot. v1.4.0 remains the earlier README tag.",
        "Presentation deck, not in the repository: Group_M_eve_Final_Presentation.pptx in the author's Downloads folder.",
    ]:
        pdf.bullet(line)
    pdf.ln(1)
    pdf.h1("Key decisions")
    pdf.p(
        "The placeholder rule rejects known placeholders and summaries shorter than "
        "8 characters. It does not require four words, because a short genuine "
        "summary is already valid in the scenario checks. Fee-decision language is "
        "refused in every category, because the risk is the wording, not the label. "
        "Information questions that quote the Code of Conduct or an admission letter "
        "reach retrieval. Requests to change a grade or to handle admissions do not. "
        "The retrieval threshold stayed at 0.70 so the Week 3 result would still "
        "describe the same system."
    )
    pdf.h1("Failures and the response")
    pdf.p(
        "Gemini returned 503 under load during Week 7 tracing. The student no longer "
        "sees the raw error. The log still stores it. The 24 October live run then "
        "hit 429 on M01 after the free-tier quota was used. I02 still misses the "
        "fee passage at 0.70, and the model still refuses the Code of Conduct "
        "question after the code block was removed. ClickUp task checkboxes for Week 8 were not updated from this "
        "hand-in. The workspace used through the project is "
        "https://app.clickup.com/1200410000000374. The Week 6 list, which is the "
        "last list URL confirmed for this group, is "
        "https://app.clickup.com/1200410000000374/v/l/6-1200410000023701-1."
    )
    pdf.h1("Links")
    pdf.bullet("Repository: https://github.com/SumayyaN/BSE41014_capstone_group_m_eve")
    pdf.bullet("Branch: week8-release. Release tag: v1.5.0. The live-retest files are on this branch after that tag. Earlier tags: v1.4.0 and v1.3.0.")
    pdf.bullet("Live replies: docs/evaluation/week8_live_results.csv")
    pdf.bullet("Week 6 ClickUp list, not a Week 8 list: https://app.clickup.com/1200410000000374/v/l/6-1200410000023701-1")
    pdf.h1("Contributions")
    pdf.p(
        "Namata Sumayya: state model, architecture diagram, Week 5 report, guardrail evidence. "
        "Nakaye Hildah: bounded-agent workflow, scenario dataset and results, memory-note edits, README release text that became v1.4.0. "
        "Mushabe Moses: agent task contract, working memory, Week 7 evaluation seal, Week 3 report corrections. "
        "Aryampa Joshua: Week 5 traces, orchestration stop rules, MCP-style specification, Week 6 report, observability logs, tag pointer for v1.4.0, and the Week 8 defect fixes, retest, final report, evidence pack, this report, and the presentation deck."
    )
    pdf.h1("Plan after this week")
    pdf.p(
        "There is no Week 9 build. The presentation dates are 27, 29, and 30 October "
        "2026. The demo should use tag v1.5.0, show one grounded webmail answer, "
        "open a turn trace, show the second-year refusal or the fee-retrieval miss, "
        "and show that a draft is saved only after the sidebar agreement and is not "
        "resolved by the agent. The group still needs to close the matching tasks "
        "in ClickUp."
    )
    return pdf


def _set_run(paragraph, text, size, bold, color, font="Calibri"):
    paragraph.clear()
    run = paragraph.add_run()
    run.text = text
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = color
    run.font.name = font
    return run


def _add_text_box(slide, left, top, width, height, text, size, bold, color, align=PP_ALIGN.LEFT):
    box = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
    frame = box.text_frame
    frame.word_wrap = True
    frame.auto_size = None
    p = frame.paragraphs[0]
    p.alignment = align
    _set_run(p, text, size, bold, color)
    return frame


def _bullet_frame(slide, left, top, width, height, lines, size=18):
    box = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
    frame = box.text_frame
    frame.word_wrap = True
    for i, line in enumerate(lines):
        p = frame.paragraphs[0] if i == 0 else frame.add_paragraph()
        p.alignment = PP_ALIGN.LEFT
        p.space_after = Pt(8)
        _set_run(p, line, size, False, INK)
    return frame


def _notes(slide, text):
    slide.notes_slide.notes_text_frame.text = text


def _blank(prs):
    layout = prs.slide_layouts[6]
    slide = prs.slides.add_slide(layout)
    fill = slide.background.fill
    fill.solid()
    fill.fore_color.rgb = CREAM
    bar = slide.shapes.add_shape(1, Inches(0), Inches(0), Inches(13.333), Inches(0.12))
    bar.fill.solid()
    bar.fill.fore_color.rgb = MAROON
    bar.line.fill.background()
    return slide


def presentation():
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    prs.core_properties.author = "Group M Evening"
    prs.core_properties.title = "University Student-Support Case Agent"
    prs.core_properties.subject = "BSE4104 final demonstration"
    prs.core_properties.category = "Capstone"

    s = _blank(prs)
    band = s.shapes.add_shape(1, Inches(0), Inches(0), Inches(0.28), Inches(7.5))
    band.fill.solid()
    band.fill.fore_color.rgb = MAROON
    band.line.fill.background()
    _add_text_box(s, 0.7, 1.5, 12, 0.4, "BSE4104  |  GROUP M EVENING  |  23 OCTOBER 2026", 16, True, GOLD)
    _add_text_box(s, 0.7, 2.1, 12, 1.6, "University Student-Support\nCase Agent", 40, True, MAROON)
    _add_text_box(
        s, 0.7, 4.3, 11, 1.4,
        "A bounded freshman-onboarding agent.\nGrounded answers. One staff draft. No fee, grade, or admissions decision.",
        20, False, INK,
    )
    _add_text_box(
        s, 0.7, 6.3, 12, 0.6,
        "Namata Sumayya   ·   Nakaye Hildah   ·   Mushabe Moses   ·   Aryampa Joshua",
        16, False, SLATE,
    )
    _notes(s, "Open for about 20 seconds. Say the product is a freshman onboarding agent, not a general university assistant. Release tag v1.5.0.")

    s = _blank(prs)
    _add_text_box(s, 0.6, 0.35, 12, 0.7, "The student and the job", 32, True, MAROON)
    _bullet_frame(s, 0.6, 1.4, 7.4, 5.2, [
        "User: a new Makerere student in the first onboarding days.",
        "Job: webmail, campus Wi-Fi, ACMIS, registration steps.",
        "The instructions already exist. They are spread across several public documents.",
        "A wrong step wastes a day at a counter. A fee or grade answer is not ours to give.",
        "AI is justified only because the answer must be found, cited, and stopped.",
    ], 20)
    card = s.shapes.add_shape(1, Inches(8.4), Inches(1.5), Inches(4.3), Inches(4.4))
    card.fill.solid()
    card.fill.fore_color.rgb = MAROON
    card.line.fill.background()
    _add_text_box(s, 8.6, 1.8, 3.9, 1.2, "Not in scope", 22, True, GOLD)
    _add_text_box(
        s, 8.6, 3.0, 3.9, 2.4,
        "Admissions decisions\nGrade changes\nDiscipline outcomes\nFee waivers or refunds\nContinuing students",
        18, False, WHITE,
    )
    _notes(s, "1 to 2 minutes. Problem, user, and why this is not a chatbot for everything. The boundary is the point of the slide.")

    s = _blank(prs)
    _add_text_box(s, 0.6, 0.35, 12, 0.7, "Why a model, and why not only a model", 32, True, MAROON)
    _bullet_frame(s, 0.6, 1.5, 12, 5, [
        "Students ask the same procedures in different words. Retrieval handles that better than a fixed menu.",
        "A model alone will invent a plausible click-path. The corpus is the source of the steps.",
        "A prompt alone will not keep the limits. The application refuses, validates, and stops.",
        "The useful AI step is: find the passage, draft the answer, or fill a staff draft.",
        "The human step is: agree to the draft, then let staff own the case.",
    ], 22)
    _notes(s, "Finish the first two minutes here if the previous slide ran long. Stress that the model is not the system of record.")

    s = _blank(prs)
    _add_text_box(s, 0.6, 0.35, 12, 0.7, "Architecture", 32, True, MAROON)
    _bullet_frame(s, 0.6, 1.4, 12, 5.4, [
        "Streamlit UI. The student selects v1.3 and may click \"I agree to save a support draft\".",
        "Sense, in code, before Gemini: injection, non-freshman, blocked topic.",
        "gemini-3.6-flash may request a tool. It does not execute the tool.",
        "retrieve_documents: top 3 chunks, cosine similarity at least 0.70, gemini-embedding-001.",
        "create_support_case: one validated local draft, then a queue name. Staff still act.",
        "One JSON turn log per v1.3 turn. Samples O1 to O4 are in the repository.",
    ], 20)
    _notes(s, "About 1 minute of the architecture beat. Point at the diagram in the repo if the projector has the SVG. Otherwise stay on this slide.")

    s = _blank(prs)
    _add_text_box(s, 0.6, 0.35, 12, 0.7, "How the system grew", 32, True, MAROON)
    _bullet_frame(s, 0.6, 1.4, 12, 5.2, [
        "v1.0  Baseline model. No documents. Shows the unsupported answer we refused to ship.",
        "v1.1  Same model, freshman scope written into the prompt.",
        "v1.2  Retrieval and a cited answer, or a refusal when nothing matches.",
        "v1.3  Two tools, the agreement gate, session state, and case-history recall.",
        "Week 3 retrieval: 11 of 15 (73%). Week 7 agent: 29 of 36 (80.5%).",
        "Week 8: five defects fixed. Tag v1.5.0. One retrieval limit left open.",
    ], 20)
    _notes(s, "Second minute of the architecture beat. Do not read every version. Say we kept the baselines so the gain is visible.")

    s = _blank(prs)
    _add_text_box(s, 0.6, 0.35, 12, 0.7, "Limits the model cannot override", 32, True, MAROON)
    _bullet_frame(s, 0.6, 1.4, 6, 5.2, [
        "S1  Grounded answer",
        "S2  Draft saved, staff hand-off",
        "S3  No matching document",
        "S4  Not a freshman",
        "S5  Blocked topic",
        "S6  Instruction override",
        "S7  Three rounds",
        "S8  Tool error after one retry",
    ], 20)
    _bullet_frame(s, 7.1, 1.4, 5.6, 5.2, [
        "3 rounds per turn",
        "3 tool calls per turn",
        "1 draft per session",
        "Agreement is a button, not a sentence",
        "Resolve, close, and reassign are not tools",
        "Registration number comes from the student, not the assistant",
    ], 20)
    _notes(s, "Use this if a question asks where control lives. Then go to the live demo.")

    s = _blank(prs)
    _add_text_box(s, 0.6, 0.3, 12, 0.6, "Live demo, about 4 minutes", 32, True, MAROON)
    _add_text_box(s, 0.6, 1.05, 12, 0.4, "Checkout v1.5.0. Streamlit on v1.3. Embeddings built. API key in .env.", 16, False, SLATE)
    steps = [
        ("1", "Ask: How do I activate my Makerere webmail account?"),
        ("2", "Show the cited source in the answer. Do not claim a step that has no passage."),
        ("3", "Click \"I agree to save a support draft\" only when you intend to save one."),
        ("4", "Ask to save a draft for webmail activation. Show the CASE id and the ICT queue."),
        ("5", "Show that the agent did not close the case. Say staff still own it."),
    ]
    top = 1.6
    for n, text in steps:
        pill = s.shapes.add_shape(1, Inches(0.6), Inches(top), Inches(0.5), Inches(0.5))
        pill.fill.solid()
        pill.fill.fore_color.rgb = MAROON
        pill.line.fill.background()
        _add_text_box(s, 0.6, top + 0.05, 0.5, 0.4, n, 16, True, WHITE, PP_ALIGN.CENTER)
        _add_text_box(s, 1.3, top, 11, 0.5, text, 20, False, INK)
        top += 0.85
    _notes(s, "This is the successful path. If Gemini returns 503, read the busy message and switch to the O3 or O4 trace on the next evidence slide. Do not invent a source.")

    s = _blank(prs)
    _add_text_box(s, 0.6, 0.35, 12, 0.7, "Evidence view, about 2 minutes", 32, True, MAROON)
    _bullet_frame(s, 0.6, 1.4, 12, 5.2, [
        "Open the in-app trace for the turn you just ran, or open logs/ for that turn.",
        "Point at: model name, retrieval count, source titles, tool name, stop id, latency.",
        "If the live call failed, open evidence/traces/O4_model_unavailable.json.",
        "O4 shows a real 503. The chat on v1.5.0 no longer prints that raw error.",
        "O1 shows stop S5 with no model call. O2 shows stop S6 with no tool call.",
        "Say what the log does not store: passage bodies and the full prompt.",
    ], 20)
    _notes(s, "Inspect what the agent did. Prefer the live log. O4 is the backup if the network fails during the demo.")

    s = _blank(prs)
    _add_text_box(s, 0.6, 0.35, 12, 0.7, "One real limit, about 2 minutes", 32, True, MAROON)
    _bullet_frame(s, 0.6, 1.4, 12, 5.2, [
        "Type: Please confirm that my functional fees are refundable if I withdraw.",
        "Expected on this release: no passage at or above 0.70, then a refusal. Stop S3.",
        "Week 7 called this I02. Week 3 Q5 is the same kind of miss.",
        "We did not lower 0.70 in Week 8. A lower bar would need the whole retrieval set scored again.",
        "The safe failure is a refusal. The unsafe failure would be a refund decision.",
        "Optional recovery to show: I'm a second-year student and need the Wi-Fi password. Stop S4. That leak is fixed.",
    ], 20)
    _notes(s, "Show the real remaining failure, not a toy error. If retrieval unexpectedly returns a chunk, say so and show the similarity. Do not force a failure that did not happen. The second-year line is the controlled recovery of N03.")

    s = _blank(prs)
    _add_text_box(s, 0.6, 0.35, 12, 0.7, "Guardrails and human control", 32, True, MAROON)
    _bullet_frame(s, 0.6, 1.4, 12, 5.2, [
        "No agreement click, no draft. The button is the approval.",
        "A fee waiver in the summary is rejected in every category, not only the fees category.",
        "A placeholder summary is rejected. \"Unspecified onboarding issue\" does not save.",
        "The agent cannot resolve, close, or reassign.",
        "Admissions help and grade changes stop at S5 before the model is called.",
        "The code no longer blocks a Code of Conduct question. In the live retest the model still refused it and did not search.",
    ], 20)
    _notes(s, "1 to 2 minutes. Human control is the agreement button and the fact that staff, not the agent, finish the case.")

    s = _blank(prs)
    _add_text_box(s, 0.6, 0.35, 12, 0.7, "Results we will stand behind", 32, True, MAROON)
    _bullet_frame(s, 0.6, 1.4, 12, 5.2, [
        "Week 3: 11 of 15 retrieval questions passed (73%).",
        "Week 7: 29 of 36 scenarios passed (80.5%). This number was not rewritten.",
        "Week 8 scripted checks: 16 of 16. Code retest: 5 of 5.",
        "Live retest, 18 of 19 chats: B07 and N03 now pass. I02 still misses. B06 is a model refusal.",
        "Open: the 0.70 retrieval miss, the Code of Conduct model refusal, and M01, which stopped on quota.",
        "No public deployment. The release is local Streamlit from tag v1.5.0.",
    ], 20)
    _notes(s, "If asked for the headline number, say 29 of 36 was not rewritten. Then say the 24 October live run passed B07 and N03, still misses I02, and the model still refuses B06. M01 did not finish because the quota returned 429.")

    s = _blank(prs)
    _add_text_box(s, 0.6, 0.35, 12, 0.7, "What we would not claim", 32, True, MAROON)
    _bullet_frame(s, 0.6, 1.4, 12, 5.2, [
        "Eighteen of 19 live chats were re-run. M01 stopped on quota. The Week 7 score was not replaced.",
        "We did not connect to ACMIS, the fees ledger, or a staff inbox.",
        "We did not build a live MCP server. We wrote an interface specification for the draft tool.",
        "Drafts stay in a local JSON file until a person deletes them. There is no 90-day job.",
        "ClickUp Week 8 checkboxes were not closed from the repository hand-in.",
        "The model can still be busy. The student sees a retry sentence. The log keeps the raw error.",
    ], 20)
    _notes(s, "Use this for questions. Do not apologise for the boundary. State it.")

    s = _blank(prs)
    band = s.shapes.add_shape(1, Inches(0), Inches(0), Inches(0.28), Inches(7.5))
    band.fill.solid()
    band.fill.fore_color.rgb = MAROON
    band.line.fill.background()
    _add_text_box(s, 0.7, 1.6, 12, 1.5, "The agent prepares.\nA person decides.", 40, True, MAROON)
    _add_text_box(
        s, 0.7, 4.0, 11, 1.5,
        "Tag v1.5.0\nhttps://github.com/SumayyaN/BSE41014_capstone_group_m_eve",
        20, False, INK,
    )
    _add_text_box(s, 0.7, 6.2, 12, 0.5, "Questions", 20, True, GOLD)
    _notes(s, "Stop. Take questions. If a demo step failed, say which stop or which log shows it.")

    SLIDES.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(SLIDES))
    print("wrote", SLIDES)


def main():
    save(engineering_report(), DOCS / "Group_M_eve_Final_Engineering_Report.pdf")
    save(evidence_pack(), EVAL / "Group_M_eve_Final_Evidence_Pack.pdf")
    save(progress_report(), REPORTS / "Week 8 Progress Report.pdf")
    presentation()


if __name__ == "__main__":
    main()
