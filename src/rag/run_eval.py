"""
Week 3 RAG evaluation: runs 15 test questions through retrieval + grounded
answer generation. Saves raw output to data/eval/rag_eval_raw.json.

Question categories:
  - Answerable (5): fully covered by the corpus
  - Partially answerable (5): partly covered, model must admit what's missing
  - Unanswerable (5): nothing in the corpus covers them
"""
import json
from pathlib import Path

from retrieve import retrieve

# We use a lightweight grounded-answer function so we don't have to
# depend on the app-level module. This is the RAG-only path.
import os
from dotenv import load_dotenv
from google import genai

env_path = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(dotenv_path=env_path)
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])


def answer_with_context(question: str, chunks: list[dict]) -> str:
    if not chunks:
        return ("I don't have that information in my sources. "
                "Please contact the support desk.")

    context_blocks = []
    for c in chunks:
        context_blocks.append(
            f"[Source: {c['source_title']} | {c['source_url']}]\n{c['text']}"
        )
    context = "\n\n---\n\n".join(context_blocks)

    prompt = f"""You are a Makerere University freshman support assistant.
Answer the student's question using ONLY the provided context.
End your answer with the source title(s) you used.
If the context does not fully answer the question, say what you know
and explicitly state what is missing.

Context:
{context}

Question: {question}

Answer:"""

    interaction = client.interactions.create(
        model="gemini-3.6-flash",
        input=prompt,
        generation_config={"thinking_level": "low"},
    )
    return interaction.output_text


QUESTIONS = [
    # ---- Answerable (5) ----
    ("Answerable", "How do I activate my Makerere webmail account?"),
    ("Answerable", "How do I connect to the MAKAIR Wi-Fi network?"),
    ("Answerable", "How do I create a MUELE account?"),
    ("Answerable", "How do I activate my ACMIS student portal?"),
    ("Answerable", "What does a fresher need to bring during joining?"),

    # ---- Partially answerable (5) ----
    ("Partially", "How do I connect to Eduroam and what if it fails?"),
    ("Partially", "How do I reset my webmail password if I forget it?"),
    ("Partially", "What are the Wi-Fi network names available to students?"),
    ("Partially", "How do I use the ACMIS mobile app to check my timetable?"),
    ("Partially", "What is the deadline for fresher registration?"),

    # ---- Unanswerable (5) ----
    ("Unanswerable", "What is the tuition fee for the astrophysics program?"),
    ("Unanswerable", "How do I schedule a postgraduate thesis defense?"),
    ("Unanswerable", "What is the score of the last Makerere basketball match?"),
    ("Unanswerable", "Can you recommend a good restaurant near campus?"),
    ("Unanswerable", "What is the Vice Chancellor's phone number?"),
]

OUT_DIR = Path(__file__).resolve().parents[2] / "docs" / "evaluation"
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_PATH = OUT_DIR / "rag_eval_raw.json"

results = []
for category, q in QUESTIONS:
    chunks = retrieve(q)
    answer = answer_with_context(q, chunks)
    entry = {
        "category": category,
        "question": q,
        "num_chunks": len(chunks),
        "sources": [c["source_title"] for c in chunks],
        "similarities": [round(c["similarity"], 3) for c in chunks],
        "answer": answer,
    }
    results.append(entry)
    print(f"\n[{category}] {q}")
    print(f"  chunks: {entry['num_chunks']}  sources: {entry['sources']}")
    print(f"  answer: {answer[:220]}...")

OUT_PATH.write_text(json.dumps(results, indent=2), encoding="utf-8")
print(f"\nSaved raw results to {OUT_PATH}")