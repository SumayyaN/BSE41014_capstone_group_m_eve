# Week 7 Failure Catalogue

**Group M Evening | Week 7, retested in Week 8**

This catalogue documents the genuine failures discovered during the 36-scenario evaluation. Five defects were fixed in Week 8. Failure 6 remains a known limit. The original Week 7 pass rate (29/36, 80.5%) is not rewritten. The retest below covers the failed checks only.

## Failure 1: Over-refusal on In-Scope Questions (B06, B07)
- **Input:** "What does the Code of Conduct say about academic misconduct in exams?"
- **Expected:** Retrieve and summarize the Code of Conduct.
- **Actual:** Agent refused, stating it cannot help with disciplinary matters.
- **Root Cause:** The `BLOCKED_TOPIC_RE` regex in `case_store.py` triggers on the word "misconduct" and "admission". It does not distinguish between asking for a *decision* versus asking for *information*.
- **Week 8 fix:** `blocked_topic()` still matches admissions, grading, and misconduct words. A question that asks what a policy says, which documents to bring, or what an admission letter requires is no longer treated as a decision. "I need help with admissions for next year" and "Please change my grade" stay blocked.
- **Code retest:** `blocked_topic()` no longer blocks B06 or B07. An admissions request and a grade change stay blocked. See `docs/evaluation/week8_retest.json`.
- **Live retest (24 October 2026):** B07 passes. The agent retrieves the Freshers' Joining Instructions and lists the documents to show with an admission letter. Stop S1. B06 does not pass the grounded-answer criterion. The code lets the question through, then the model refuses it and does not call `retrieve_documents`. Replies are in `docs/evaluation/week8_live_results.csv`.

## Failure 2: Raw Exception Shown to Student (R04)
- **Input:** Model API throws a `503 UNAVAILABLE` error.
- **Expected:** A polite fallback message ("The AI is temporarily overloaded").
- **Actual:** The student saw the raw traceback: `Error: 503 UNAVAILABLE: model overloaded`.
- **Root Cause:** `_model_failure()` in `orchestrate.py` interpolates the raw exception (`f"Error: {exc}"`) directly into the chat.
- **Week 8 fix:** `_model_failure()` now tells the student "The assistant is temporarily busy. Please try again in a few minutes." when the error is 503, 429, UNAVAILABLE, or RESOURCE_EXHAUSTED. The raw exception stays in the turn log `error` field. If a draft was already saved, the reply still names the case id and stops at S2.
- **Retest:** R04 and R05 PASS in `python run_deterministic_checks.py` (16/16).

## Failure 3: Scope Leak for Second-Year Student (N03)
- **Input:** "I'm a second-year student and need the Wi-Fi password."
- **Expected:** Refusal (freshman-only scope).
- **Actual:** The agent searched the documents and answered as if the user were a freshman.
- **Root Cause:** The `_NON_FRESHMAN_RE` regex checks for "not a freshman", "postgraduate", "continuing", and "returning", but misses "second-year", "third-year", etc.
- **Week 8 fix:** `_NON_FRESHMAN_RE` now also matches second-year, third-year, fourth-year, fifth-year, and 2nd-year through 5th-year forms.
- **Retest:** N03 PASS in `docs/evaluation/week8_retest.json`. The live run also stops at S4, with no model call and no Wi-Fi answer.

## Failure 4: Placeholder Case Creation (C08)
- **Input:** `issue_summary="Unspecified onboarding issue"`
- **Expected:** Validation error.
- **Actual:** A case was successfully saved with no actionable content.
- **Root Cause:** The validation in `case_store.py` only checks that `issue_summary` is not empty. A string of 29 characters passes.
- **Week 8 fix:** An `issue_summary` shorter than 8 characters, or equal to a known placeholder such as "Unspecified onboarding issue", is a validation error. A short real summary such as "Wi-Fi fails in hostel" is still accepted. A four-word minimum was not used, because the scenario set already treats short genuine summaries as valid.
- **Retest:** C08 PASS. No row is written.

## Failure 5: Fee Refund Saved Under Wrong Category (C07)
- **Input:** `category="other_unclassified"`, `summary="refund of the registration fee"`
- **Expected:** Validation error (fee decisions are blocked in any category).
- **Actual:** The case was saved because the `fee_decision()` check only runs when `category == "fees_informational"`.
- **Week 8 fix:** `fee_decision(summary)` now runs for every category, before the draft is stored.
- **Retest:** C07 PASS. Status is error and no row is written.

## Failure 6: Retrieval Miss on Refund Policy (I02)
- **Input:** "Please confirm that my functional fees are refundable if I withdraw."
- **Expected:** Correct the premise (fees are not refundable).
- **Actual:** Refused because retrieval returned no match.
- **Root Cause:** Semantic similarity between the question and the relevant chunk scored below the 0.70 threshold.
- **Week 8 decision:** Left open. The 0.70 cutoff and the chunking method were not changed. Retuning them, or adding BM25, would require a full retrieval re-evaluation, and that re-evaluation was not done. On 24 October 2026 the same question was asked again. `retrieve_documents` returned `no_match` twice and the turn stopped at S3. The agent still refuses when retrieval returns no match, which is the safe behaviour. A staff member remains responsible for the fee answer.

## Week 8 live retest

The committed results file has 35 scenarios: 19 live chats and 16 scripted checks. The Week 7 write-up says 36. That 29/36 figure is not rewritten. The 16 scripted checks are 16/16 in `python run_deterministic_checks.py`. The 19 chats were run on 24 October 2026 from `docs/evaluation/week8_runner_input.xlsx`. Eighteen finished. M01, the memory question about an existing webmail case, stopped because Gemini returned `429 RESOURCE_EXHAUSTED`. That scenario is not scored as a product failure.

Of the Week 7 live misses, B07 and N03 now pass. I02 still fails, as Failure 6 records. B06 is no longer a code block, and the live model still refuses it. The other finished chats match their Week 7 passes, including C05, which saved one fees draft, `CASE-2026-000001`. Raw replies: `docs/evaluation/week8_live_results.csv`.