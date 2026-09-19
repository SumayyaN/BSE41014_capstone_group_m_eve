RAG Failure Catalogue  Week 3

Group M Evening, Week 3
Date: 19th September 2026

Each failure below was observed during the 15-case evaluation. The goal is to document real problems, their root cause, and a proposed fix, rather than to hide them.

Failure 1 : False refusal on an answerable question

Question: What does a fresher need to bring during joining?

Expected behaviour: Retrieve the relevant section from Freshers' Joining Instructions 2026/2027 and answer.

Actual behaviour: The retriever returned 0 chunks above the 0.70 similarity threshold, so the model responded: "I don't have that information in my sources."

Root cause: The joining instructions document is 113,435 characters long and was split into 65 chunks. The specific chunk that lists required items likely scored below 0.70 because the query words ("bring", "fresher", "joining") do not overlap strongly with the chunk's phrasing (for example, "requirements checklist" or "documents to present"). Semantic similarity is diluted by the document's size and formal tone.

Proposed fix: Increase the number of retrieved chunks from 3 to 5 and lower the threshold to 0.68 for a trial run, then measure the precision-versus-recall trade-off. A more targeted fix is to add metadata filtering so that onboarding-related questions preferentially hit the joining instructions document.

Failure 2 : Corpus gap for a partial question

Question: How do I reset my webmail password if I forget it?

Expected behaviour: Answer the recovery steps, or explicitly say they are not in the corpus.

Actual behaviour: Refused. The model correctly stated it does not have the information.

Root cause: The corpus contains the activation guide for webmail but no recovery guide. Password recovery is handled by the ICT helpdesk, and no public document covering it was included in the corpus.

Proposed fix: Two-part. First, add a public ICT password recovery guide to the corpus if one exists. Second, if it does not exist, add a static fallback chunk describing the general escalation path (contact the ICT helpdesk with your student ID) so the model has something concrete to say instead of a generic refusal.

Failure 3 _ Dynamic content excluded from the corpus

Question: What is the deadline for fresher registration?

Expected behaviour: Provide the deadline date and cite the academic calendar.

Actual behaviour: Refused.

Root cause: The registration deadline is published on a dynamic university portal, not in a static PDF or HTML page. The Corpus/Source Register explicitly excluded the dynamic timetable portal because it cannot be embedded as static text.

Proposed fix: Either accept this as a scope limitation and route deadline-related questions to a support ticket rather than an answer, or add a small manually curated chunk that summarises publicly known deadlines and clearly marks them as "verify on the portal". The first option is safer and better matches the assignment's bounded-agent philosophy.

Summary of Fixes

Failure 1: False refusal on an answerable question. Proposed fix: increase top-k, lower threshold, add metadata filtering. Address in Week 4 to 5.

Failure 2:  Corpus gap for a partial question. Proposed fix: add ICT recovery guide or a fallback chunk. Address in Week 4.

Failure 3: Dynamic content excluded from the corpus. Proposed fix: route to support ticket instead of answering. Address in Week 5.