# RAG Pipeline — Setup & Run Order

This folder builds the retrieval-augmented generation (RAG) pipeline that
grounds the agent's answers in real Makerere University documents (see
`docs/requirements/corpus-source-register.md` for the full source list).

The raw downloaded documents, extracted text, and embeddings are **not**
committed to this repository (they're regenerable and/or large — see
`.gitignore`). After cloning the repo, you must run the pipeline once
locally before the app will give grounded (v1.2) answers.

## Prerequisites

1. Install dependencies from the repo root:
   ```
   pip install -r requirements.txt
   ```
2. Make sure you have a `.env` file at the repo root containing:
   ```
   GEMINI_API_KEY=your_key_here
   ```
   Get a free key at https://aistudio.google.com

## Run order

Run these from inside `src/rag/`, **in this exact order** — each step depends
on the output of the one before it:

1. **`python download_sources.py`**
   Downloads all sources listed in the Corpus/Source Register to
   `data/raw_docs/`. Takes a few seconds. Safe to re-run any time.

2. **`python extract_text.py`**
   Extracts plain text from the downloaded PDFs/HTML pages into
   `data/extracted/`, plus a `manifest.json` recording each source's title
   and URL for citation purposes.

3. **`python chunk_text.py`**
   Splits the extracted text into ~1,500-character chunks, saved to
   `data/chunks/chunks.json`. This file IS committed to the repo (it's
   small, human-readable text — useful to see without re-running anything).

4. **`python embed_chunks.py`**
   Generates an embedding vector for every chunk using Gemini's embedding
   model, saved to `data/chunks/chunks_with_embeddings.json`.
   **This step uses real API quota** (Gemini's free tier has a daily limit —
   see note below) and can take a minute or two for ~90 chunks.
   If it stops partway (e.g. due to a quota error), it's safe to just run it
   again — it saves progress after every batch and resumes automatically
   rather than starting over.

Once step 4 finishes, retrieval and the RAG-enabled app (prompt version
v1.2) are ready to use.

## Running the app

From the repo root:
```
python -m streamlit run src/app.py
```
Select **v1.2** in the sidebar to get RAG-grounded, source-cited answers.
v1.0 and v1.1 remain non-RAG baselines for comparison (see
`docs/requirements/prompt-specification.md`).

## Notes

- **Gemini's free tier quota resets daily**, roughly 10:00 AM East Africa
  Time. If `embed_chunks.py` fails with a `RESOURCE_EXHAUSTED` / `429`
  error, you've likely hit the daily limit — wait and re-run later; it will
  resume from wherever it stopped.
- The similarity threshold used in retrieval (`MIN_SIMILARITY` in
  `retrieve.py`) was tuned against real test questions — see
  `docs/evaluation/` for the reasoning and the retrieval failures this
  uncovered.
- The dynamic timetable portal (`timetable.mak.ac.ug`) is intentionally
  excluded from the corpus, per the Corpus/Source Register's own note that
  it cannot be embedded as static text.