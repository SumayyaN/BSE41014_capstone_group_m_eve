# Final Evaluation and Evidence Pack

**Group M Evening University Student-Support Case Agent**
**Week 8 Final Release**

This folder contains the verified evidence that the agent is bounded, grounded, and safe. The evidence is organized by project phase.

## 1. Observability and Traces (`/traces`)
- `T1-grounded_answer.json`
- `T2_case_draft.json` 
- `T3_failure_recovery.json` 
*These traces prove that every tool call, retrieval, and stop condition is logged and inspectable.*

## 2. Evaluation Results (`/evaluation`)
- `week3_rag_eval.md` — The initial 15-case RAG evaluation (73% pass rate), proving the system grounds answers in Makerere documents.
- `week7_scenario_results.csv` — The final 36-scenario evaluation (80.5% pass rate) covering Normal, Edge, Incorrect-Information, Adversarial, Tool-Failure, and Unauthorized-Action cases.
- `week7_failure_catalogue.md` — Documents the 6 genuine failures found during evaluation and the remediation plan applied for the final release.
- *These files prove the system was rigorously tested against adversarial and edge cases.*

## 3. Persistent Memory Demo (`/memory_demo`)
- `01_case_created.png` — Screenshot of a case draft being created in Session 1.
- `02_prior_case_recall.png` — Screenshot of the agent recalling the case in Session 2 (after a browser restart).
-
- *This proves the system maintains justified memory without using the LLM to hallucinate state.*

## 4. Guardrails (`screenshoots/guardrails`)
- `G09-1.png` 
- `g09-2.png` .
- *This proves the agent is bounded and cannot be jailbroken to execute unauthorized actions.*