# Week 7 Failure Catalogue

**Group M Evening | Week 7**


This catalogue documents the genuine failures discovered during the 36-scenario evaluation. Fixes are scheduled for Week 8 hardening.

## Failure 1: Over-refusal on In-Scope Questions (B06, B07)
- **Input:** "What does the Code of Conduct say about academic misconduct in exams?"
- **Expected:** Retrieve and summarize the Code of Conduct.
- **Actual:** Agent refused, stating it cannot help with disciplinary matters.
- **Root Cause:** The `BLOCKED_TOPIC_RE` regex in `case_store.py` triggers on the word "misconduct" and "admission". It does not distinguish between asking for a *decision* versus asking for *information*.
- **Remediation Plan (Week 8):** Adjust the regex to look for decision-making verbs near the blocked words (e.g., "appeal my misconduct" or "check my admission status").

## Failure 2: Raw Exception Shown to Student (R04)
- **Input:** Model API throws a `503 UNAVAILABLE` error.
- **Expected:** A polite fallback message ("The AI is temporarily overloaded").
- **Actual:** The student saw the raw traceback: `Error: 503 UNAVAILABLE: model overloaded`.
- **Root Cause:** `_model_failure()` in `orchestrate.py` interpolates the raw exception (`f"Error: {exc}"`) directly into the chat.
- **Remediation Plan (Week 8):** Catch standard exceptions and map them to user-friendly strings before displaying.

## Failure 3: Scope Leak for Second-Year Student (N03)
- **Input:** "I'm a second-year student and need the Wi-Fi password."
- **Expected:** Refusal (freshman-only scope).
- **Actual:** The agent searched the documents and answered as if the user were a freshman.
- **Root Cause:** The `_NON_FRESHMAN_RE` regex checks for "not a freshman", "postgraduate", "continuing", and "returning", but misses "second-year", "third-year", etc.
- **Remediation Plan (Week 8):** Expand the regex to `\b([2-5]|second|third|fourth|fifth)[- ]year\b`.

## Failure 4: Placeholder Case Creation (C08)
- **Input:** `issue_summary="Unspecified onboarding issue"`
- **Expected:** Validation error.
- **Actual:** A case was successfully saved with no actionable content.
- **Root Cause:** The validation in `case_store.py` only checks that `issue_summary` is not empty. A string of 29 characters passes.
- **Remediation Plan (Week 8):** Add a minimum length check (e.g., 10 words) or block known placeholder phrases.

## Failure 5: Fee Refund Saved Under Wrong Category (C07)
- **Input:** `category="other_unclassified"`, `summary="refund of the registration fee"`
- **Expected:** Validation error (fee decisions are blocked in any category).
- **Actual:** The case was saved because the `fee_decision()` check only runs when `category == "fees_informational"`.
- **Remediation Plan (Week 8):** Move the `fee_decision(summary)` check outside the category-specific `if` block so it applies to all categories.

## Failure 6: Retrieval Miss on Refund Policy (I02)
- **Input:** "Please confirm that my functional fees are refundable if I withdraw."
- **Expected:** Correct the premise (fees are not refundable).
- **Actual:** Refused because retrieval returned no match.
- **Root Cause:** Semantic similarity between the question and the relevant chunk scored below the 0.70 threshold.
- **Remediation Plan (Week 8):** Adjust the chunking strategy or add keyword-based fallback (BM25) for documents with dense financial policy text.