# Makerere University Freshman Support Agent
**BSE4104 AI Agentic Systems — Capstone Project**
Group M (Evening) | Makerere University

---

## What This Is

A RAG-powered AI support agent that helps Makerere University freshmen with onboarding questions — webmail setup, campus Wi-Fi, ACMIS portal activation, and registration. It grounds every answer in real university documents and can save a support draft for staff follow-up.

The reproducible final release is Git tag **`v1.5.0`**. Tag `v1.3.0` is the Week 7 evaluation snapshot. Tag `v1.4.0` is the README release before the Week 8 defect fixes. To run the final release:

```
git clone https://github.com/SumayyaN/BSE41014_capstone_group_m_eve.git
cd BSE41014_capstone_group_m_eve
git checkout v1.5.0
```

Then follow Prerequisites, RAG Pipeline Setup, and Running the App below.

Four prompt versions are included for comparison:

| Version | Description |
|---------|-------------|
| v1.0 | Baseline — no RAG, no tools, no memory |
| v1.1 | Scoped baseline — freshman-only, no RAG, no tools |
| v1.2 | RAG-grounded answers with source citations |
| v1.3 | Full agent — RAG + support case tool + session memory |

---

## Project Structure

```
BSE41014_capstone_group_m_eve/
├── src/
│   ├── app.py                      # Streamlit UI
│   ├── llm_client.py               # Gemini calls + RAG injection (v1.0–v1.2)
│   ├── run_deterministic_checks.py # Week 7 scripted scenario checks
│   ├── week8_retest.py             # Week 8 retest of the hardened failures
│   ├── run_scenarios.py            # Week 7 live E2E scenario runner
│   ├── agent/
│   │   └── state.py                # Session state (Agent Task Contract §4)
│   ├── observability/
│   │   └── turn_log.py             # Week 7 turn log (model, retrieval, tools, latency)
│   ├── rag/
│   │   ├── download_sources.py     # Step 1: download corpus documents
│   │   ├── extract_text.py         # Step 2: extract text from PDFs/HTML
│   │   ├── chunk_text.py           # Step 3: split into ~1500-char chunks
│   │   ├── embed_chunks.py         # Step 4: generate Gemini embeddings
│   │   ├── retrieve.py             # Cosine similarity retrieval
│   │   └── run_eval.py             # Week 3 RAG evaluation (15 questions)
│   └── tools/
│       ├── orchestrate.py          # Sense→Plan→Act→Observe loop (v1.3)
│       ├── handlers.py             # retrieve_documents + create_support_case
│       └── case_store.py           # Local draft storage + validation
├── prompts/
│   ├── v1.0_baseline.txt
│   ├── v1.1_baseline.txt
│   ├── v1.2_baseline.txt
│   └── v1.3_tools.txt
├── data/
│   └── chunks/
│       └── chunks.json             # Committed — pre-chunked corpus text
├── docs/
│   ├── Architecture/               # Architecture diagrams (SVG, PNG, PDF)
│   ├── evaluation/                 # RAG eval, Week 7 scenarios, failure catalogue
│   ├── requirements/               # Agent Task Contract, Prompt Spec, Tool Catalogue
│   └── weekly-reports/             # Week 1–8 progress reports
├── evidence/
│   ├── screenshots/                # Guardrails, ClickUp, GitHub evidence
│   └── traces/                     # Week 5 T1–T3 and Week 7 O1–O4 samples
├── .env.example
├── requirements.txt
└── README.md
```

---

## Prerequisites

**Python 3.11+** is required.

1. Clone the repository and install dependencies from the repo root:
   ```
   pip install -r requirements.txt
   ```

2. Copy `.env.example` to `.env` and add your Gemini API key:
   ```
   GEMINI_API_KEY=your_key_here
   ```
   Get a free key at https://aistudio.google.com

---

## RAG Pipeline Setup (required before running v1.2 or v1.3)

Run these from inside `src/rag/`, **in this exact order**:

```
cd src/rag
python download_sources.py
python extract_text.py
python chunk_text.py
python embed_chunks.py
```

| Step | Script | Output | Notes |
|------|--------|--------|-------|
| 1 | `download_sources.py` | `data/raw_docs/` | Downloads PDFs and HTML pages |
| 2 | `extract_text.py` | `data/extracted/` + `manifest.json` | Extracts plain text |
| 3 | `chunk_text.py` | `data/chunks/chunks.json` | ~1500-char chunks |
| 4 | `embed_chunks.py` | `data/chunks/chunks_with_embeddings.json` | Uses Gemini API quota |

Step 4 uses real API quota. If it stops with a `RESOURCE_EXHAUSTED` / `429` error, re-run it — it resumes from where it stopped. The free tier quota resets daily (~10:00 AM EAT).

`chunks.json` (Step 3 output) is committed to the repo so you can inspect the corpus without re-running Steps 1–3.

---

## Running the App

From the **repo root**:
```
python -m streamlit run src/app.py
```

- Select **v1.2** in the sidebar for RAG-grounded, source-cited answers.
- Select **v1.3** for the full agent with the support case tool.
- v1.0 and v1.1 are non-RAG baselines kept for comparison.

For v1.3, the support case tool only becomes available after clicking **"I agree to save a support draft"** in the sidebar.

---

## Running the Evaluations

**Deterministic checks** (no API calls, no quota used):
```
cd src
python run_deterministic_checks.py
```
Outputs a PASS/FAIL line per scenario and writes `deterministic_results.json`.

**Week 3 RAG evaluation** (15 questions, uses API quota):
```
cd src/rag
python run_eval.py
```
Outputs results to `docs/evaluation/rag_eval_raw.json`.

**Week 7 live E2E scenarios** (uses API quota):
```
cd src
python run_scenarios.py ../docs/evaluation/Group_M_Week7_Scenario_Evaluation.xlsx --repeat 1
```

---

## Agent Design

The v1.3 agent follows the **Sense → Plan/Decide → Act → Observe → Stop** loop defined in the Agent Task Contract (see `docs/requirements/`):

- **Sense**: deterministic pre-checks block prompt injection (S6), out-of-scope users (S4), and blocked topics (S5) before the model is ever called.
- **Plan/Decide**: Gemini decides which tool to call (retrieve or create case).
- **Act**: the orchestration layer — not the model — executes the call.
- **Observe**: tool results are fed back to the model.
- **Stop**: one of 8 documented stop conditions (S1–S8) ends the turn.

Limits enforced in code (not by the model):
- Max 3 orchestration rounds per turn
- Max 3 tool calls per turn
- Max 1 support draft per session

---

## Evaluation Results Summary

| Week | Scope | Result |
|------|-------|--------|
| Week 3 | RAG retrieval (15 questions) | 11/15 pass (73%) |
| Week 7 | Full agent (36 scenarios) | 29/36 pass (80.5%) |

Known failures are documented in `docs/evaluation/failure_catalogue_week7.md`. Week 8 fixed five of them. Re-run the scripted checks with `python week8_retest.py` and `python run_deterministic_checks.py` from `src/`. The deterministic suite is 16/16 after the fixes.

Still open on this release:

- Some fee-policy questions score below the 0.70 retrieval cutoff (Week 7 scenario I02, and Week 3 Q5). The cutoff was not retuned.
- A live turn can take longer than 10 seconds. Week 7 recorded 13.6 seconds on a memory lookup and 12.5 seconds on case creation.

Week 7 turn logs are written to `logs/` and are not committed. Checked-in samples are `evidence/traces/O1_blocked_topic.json` through `O4_model_unavailable.json`. Regenerate them with `python src/traces/run_week7_observability.py`.

---

## Key Documents

| Document | Location |
|----------|----------|
| Agent Task Contract | `docs/requirements/Agent Task Contract M EVE.pdf` |
| Prompt Specification | `docs/requirements/Group M - Prompt Specification v1.0.pdf` |
| Tool Catalogue & API Schemas | `docs/requirements/Tool_Catalogue_and_API_Schemas.pdf` |
| Corpus/Source Register | `docs/requirements/Group M - Corpus Source Register.pdf` |
| Architecture Diagram | `docs/Architecture/Group_M_eve_Agent Architecture Diagram.svg` |
| Week 7 Evaluation Report | `docs/evaluation/week7_evaluation.md` |
| Failure Catalogue | `docs/evaluation/failure_catalogue_week7.md` |
| Observability evidence | `docs/evaluation/Group_M_eve_Observability_Tracing_Evidence.pdf` |
| Week 8 retest | `docs/evaluation/week8_retest.json` |
| Final engineering report | `docs/Group_M_eve_Final_Engineering_Report.pdf` |
| Final evidence pack | `docs/evaluation/Group_M_eve_Final_Evidence_Pack.pdf` |
| Week 8 progress report | `docs/weekly-reports/Week 8 Progress Report.pdf` |

---

## Notes

- The dynamic timetable portal (`timetable.mak.ac.ug`) is intentionally excluded from the corpus — it cannot be embedded as static text (see Corpus/Source Register).
- The similarity threshold (`MIN_SIMILARITY = 0.70` in `retrieve.py`) was tuned against real test questions — see `docs/evaluation/rag_eval.md` for the reasoning.
- `data/raw_docs/`, `data/extracted/`, and `data/chunks/chunks_with_embeddings.json` are excluded from version control (regenerable). Only `data/chunks/chunks.json` is committed.
