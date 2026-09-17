"""
Retrieval step: given a student's question, embed it and find the most
relevant chunks from data/chunks/chunks_with_embeddings.json using cosine
similarity. This is the piece that plugs into llm_client.py to ground
answers in the real corpus instead of the model's general knowledge.
"""
import json
import os
from pathlib import Path

import numpy as np
from dotenv import load_dotenv
from google import genai
from google.genai import types

env_path = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(dotenv_path=env_path)

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

CHUNKS_PATH = Path(__file__).resolve().parents[2] / "data" / "chunks" / "chunks_with_embeddings.json"

EMBEDDING_MODEL = "gemini-embedding-001"
TOP_K = 3                      # how many chunks to retrieve per question
MIN_SIMILARITY = 0.70          # chosen after comparing 0.5 / 0.65 / 0.70 against real test
                                # questions (see docs/evaluation/rag-evaluation.md) - favors
                                # fewer false positives over fewer false negatives, since a
                                # support agent answering the wrong topic is worse than one
                                # that says "I don't know" too often

_chunks_cache = None


def load_chunks() -> list[dict]:
    global _chunks_cache
    if _chunks_cache is None:
        _chunks_cache = json.loads(CHUNKS_PATH.read_text(encoding="utf-8"))
    return _chunks_cache


def embed_query(question: str) -> list[float]:
    result = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=question,
        config=types.EmbedContentConfig(task_type="RETRIEVAL_QUERY"),
    )
    return result.embeddings[0].values


def cosine_similarity(a: list[float], b: list[float]) -> float:
    a_arr = np.array(a)
    b_arr = np.array(b)
    return float(np.dot(a_arr, b_arr) / (np.linalg.norm(a_arr) * np.linalg.norm(b_arr)))


def retrieve(question: str, top_k: int = TOP_K) -> list[dict]:
    """
    Return the top_k most relevant chunks for the question, each annotated
    with its similarity score. Chunks below MIN_SIMILARITY are excluded -
    this is what lets the system honestly say "I don't know" when nothing
    in the corpus actually covers the question, instead of forcing in the
    closest (but irrelevant) match.
    """
    chunks = load_chunks()
    query_vector = embed_query(question)

    scored = []
    for chunk in chunks:
        score = cosine_similarity(query_vector, chunk["embedding"])
        scored.append({**chunk, "similarity": score})

    scored.sort(key=lambda c: c["similarity"], reverse=True)
    relevant = [c for c in scored[:top_k] if c["similarity"] >= MIN_SIMILARITY]

    return relevant


if __name__ == "__main__":
    # Quick manual test - try a few questions from the terminal.
    # Categorized per the Week 3 requirement: answerable, partially
    # answerable, and deliberately unanswerable questions.
    test_questions = [
        ("Answerable", "How do I set up my university webmail?"),
        ("Answerable", "How do I connect to campus Wi-Fi?"),
        ("Partially answerable", "What is the tuition fee for the astrophysics program?"),
        ("Unanswerable (out of scope)", "What's the score of the last Makerere basketball match?"),
        ("Unanswerable (out of scope)", "How do I schedule a postgraduate thesis defense?"),
        ("Unanswerable (out of scope)", "Can you recommend a good restaurant near campus?"),
    ]
    for category, q in test_questions:
        print(f"\n[{category}] Question: {q}")
        results = retrieve(q)
        if not results:
            print("  -> No sufficiently relevant chunks found (below similarity threshold).")
        for r in results:
            print(f"  -> [{r['similarity']:.3f}] {r['source_title']} ({r['chunk_id']})")