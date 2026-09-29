**RAG Evaluation** (15 Cases)

Group M Evening | Week 3
Date: 19th September 2026

Corpus: 8 Makerere freshman onboarding documents → 90 chunks
Retriever: top-3 chunks, cosine similarity ≥ 0.70
Model: gemini-3.6-flash with grounded prompt

|*Summary*

Answerable questions: 4 out of 5 passed (80%)
Partially answerable questions: 2 out of 5 passed (40%)
Unanswerable questions: 5 out of 5 passed (100%)
Overall: 11 out of 15 passed (73%)

Answerable Questions

Q1. How do I activate my Makerere webmail account?
Chunks retrieved: 3
Sources: Activating Your Makerere Webmail Account (twice), Freshers' Joining Instructions 2026/2027
Top similarity: 0.738
Result: Pass — correct steps delivered, sources cited

Q2. How do I connect to the MAKAIR Wi-Fi network?
Chunks retrieved: 3
Sources: New Guidelines For Connecting To MAKAIR, Eduroam and access to the Metro-Eduroam Network, Freshers' Joining Instructions 2026/2027
Top similarity: 0.717
Result: Pass — per-device steps delivered, sources cited

Q3. How do I create a MUELE account?
Chunks retrieved: 2
Sources: How to Create a MUELE Account, Student Tutorial on Accessing and Using MUELE
Top similarity: above 0.75
Result: Pass — correct prerequisite (webmail) and steps delivered

Q4. How do I activate my ACMIS student portal?
Chunks retrieved: 3
Sources: How To Activate Your Mak Student's Portal (ACMIS), Makerere University ACMIS Mobile App Guide, Freshers' Joining Instructions 2026/2027
Top similarity: above 0.72
Result: Pass — activation flow delivered, sources cited

Q5. What does a fresher need to bring during joining?
Chunks retrieved: 0
Result: Fail — false refusal. The joining instructions document covers this content but the relevant chunk scored below 0.70.

Partially Answerable Questions

Q6. How do I connect to Eduroam and what if it fails?
Chunks retrieved: 0
Result: Refused. Corpus covers Eduroam setup but not troubleshooting.

Q7. How do I reset my webmail password if I forget it?
Chunks retrieved: 0
Result: Refused. Corpus covers activation only, not recovery.

Q8. What are the Wi-Fi network names available to students?
Chunks retrieved: 0
Result: Refused. MAKAIR and Eduroam exist in the corpus but are not listed together in one chunk.

Q9. How do I use the ACMIS mobile app to check my timetable?
Chunks retrieved: 1
Sources: Makerere University ACMIS Mobile App Guide
Top similarity: above 0.72
Result: Pass — partial answer delivered, missing part acknowledged

Q10. What is the deadline for fresher registration?
Chunks retrieved: 0
Result: Refused. Registration deadlines are published on a dynamic portal, not in static text.

Unanswerable Questions

Q11. What is the tuition fee for the astrophysics program?
Chunks retrieved: 0
Result: Pass — correctly refused

Q12. How do I schedule a postgraduate thesis defense?
Chunks retrieved: 0
Result: Pass — correctly refused (out of freshman scope)

Q13. What is the score of the last Makerere basketball match?
Chunks retrieved: 0
Result: Pass — correctly refused

Q14. Can you recommend a good restaurant near campus?
Chunks retrieved: 0
Result: Pass — correctly refused

Q15. What is the Vice Chancellor's phone number?
Chunks retrieved: 1
Sources: Freshers' Joining Instructions 2026/2027
Result: Pass — retrieved the VC bio chunk but correctly refused to provide the phone number since it is not in the corpus

Observations

The retriever is conservative — it prefers refusal over wrong answers, which is the correct behaviour for a support agent.

Similarity scores for correctly retrieved answerable questions cluster between 0.717 and 0.75, meaning the 0.70 threshold is tight. Small phrasing changes could tip a valid question into a false refusal.

All five unanswerable questions were correctly refused. This is the strongest part of the system.

Three partially answerable questions were refused when they could have been partially answered. These are documented in the failure catalogue.