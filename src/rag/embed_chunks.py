"""
Generate embeddings for every chunk in data/chunks/chunks.json using Gemini's
embedding model, and save the result (chunk text + metadata + embedding vector)
to data/chunks/chunks_with_embeddings.json.

Chunks are sent in small batches (not one-by-one) to reduce the number of API
calls against the free-tier rate limit, with a short delay between batches
and a retry with backoff if a call is rate-limited (HTTP 429).
"""
import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types

env_path = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(dotenv_path=env_path)

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

CHUNKS_DIR = Path(__file__).resolve().parents[2] / "data" / "chunks"
CHUNKS_PATH = CHUNKS_DIR / "chunks.json"
OUTPUT_PATH = CHUNKS_DIR / "chunks_with_embeddings.json"

EMBEDDING_MODEL = "gemini-embedding-001"
BATCH_SIZE = 10          # chunks per API call
DELAY_BETWEEN_BATCHES = 2.0   # seconds, kept conservative for the free tier
MAX_RETRIES = 3


def embed_batch(texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts, retrying with backoff on rate-limit errors."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            result = client.models.embed_content(
                model=EMBEDDING_MODEL,
                contents=texts,
                config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT"),
            )
            return [emb.values for emb in result.embeddings]
        except Exception as e:
            if attempt == MAX_RETRIES:
                raise
            wait = 5 * attempt
            print(f"  [retry] attempt {attempt} failed ({e}); waiting {wait}s")
            time.sleep(wait)


def load_existing_progress() -> list[dict]:
    """Load already-embedded chunks from a previous run, if any, so we can resume."""
    if OUTPUT_PATH.exists():
        existing = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
        print(f"Found existing progress: {len(existing)} chunks already embedded.")
        return existing
    return []


def save_progress(embedded_chunks: list[dict]):
    OUTPUT_PATH.write_text(json.dumps(embedded_chunks), encoding="utf-8")


def embed_all():
    chunks = json.loads(CHUNKS_PATH.read_text(encoding="utf-8"))
    print(f"Loaded {len(chunks)} chunks total.")

    embedded_chunks = load_existing_progress()
    already_done_ids = {c["chunk_id"] for c in embedded_chunks}
    remaining = [c for c in chunks if c["chunk_id"] not in already_done_ids]

    if not remaining:
        print("All chunks already embedded. Nothing to do.")
        return embedded_chunks

    print(f"{len(remaining)} chunks remaining to embed.\n")

    for i in range(0, len(remaining), BATCH_SIZE):
        batch = remaining[i:i + BATCH_SIZE]
        texts = [c["text"] for c in batch]

        try:
            vectors = embed_batch(texts)
        except Exception as e:
            print(f"\n[STOPPED] Could not embed batch starting at chunk {batch[0]['chunk_id']}: {e}")
            print(f"Progress so far ({len(embedded_chunks)} chunks) has been saved.")
            print("Re-run this script later (e.g. after quota resets) to resume from here.")
            return embedded_chunks

        for chunk, vector in zip(batch, vectors, strict=True):
            embedded_chunks.append({**chunk, "embedding": vector})

        # Save after every batch, not just at the end, so a later failure
        # never loses work that already succeeded.
        save_progress(embedded_chunks)

        print(f"[OK] embedded {len(embedded_chunks)}/{len(chunks)} chunks (saved)")

        if i + BATCH_SIZE < len(remaining):
            time.sleep(DELAY_BETWEEN_BATCHES)

    print(f"\nDone. {len(embedded_chunks)} embedded chunks saved to {OUTPUT_PATH}")
    return embedded_chunks


if __name__ == "__main__":
    embed_all()