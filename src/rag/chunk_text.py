"""
Split extracted text files into smaller chunks suitable for retrieval.
Reads data/extracted/*.txt (plus manifest.json for source titles/urls) and
writes data/chunks/chunks.json - a list of {chunk_id, text, source_id,
source_title, source_url} ready to be embedded in the next step.

Chunking strategy: split by paragraph (blank-line-separated blocks), then
group consecutive paragraphs together up to a target size (~1500 characters,
roughly 250-350 words) so each chunk is a coherent, self-contained piece of
text rather than a single sentence or an entire document.
"""
import json
from pathlib import Path

EXTRACTED_DIR = Path(__file__).resolve().parents[2] / "data" / "extracted"
CHUNKS_DIR = Path(__file__).resolve().parents[2] / "data" / "chunks"
CHUNKS_DIR.mkdir(parents=True, exist_ok=True)

TARGET_CHUNK_CHARS = 1500  # roughly 250-350 words per chunk
MIN_CHUNK_CHARS = 200      # avoid tiny leftover fragments as their own chunk


def split_into_paragraphs(text: str) -> list[str]:
    # Split on blank lines; fall back to single newlines if the source has none
    raw_paragraphs = [p.strip() for p in text.split("\n\n")]
    paragraphs = [p for p in raw_paragraphs if p]
    if len(paragraphs) <= 1:
        raw_paragraphs = [p.strip() for p in text.split("\n")]
        paragraphs = [p for p in raw_paragraphs if p]
    return paragraphs


def group_paragraphs_into_chunks(paragraphs: list[str]) -> list[str]:
    chunks = []
    current = []
    current_len = 0

    for para in paragraphs:
        if current_len + len(para) > TARGET_CHUNK_CHARS and current:
            chunks.append("\n\n".join(current))
            current = []
            current_len = 0
        current.append(para)
        current_len += len(para)

    if current:
        # Merge a too-small trailing chunk into the previous one rather than
        # leaving a near-empty fragment as its own retrievable chunk
        last_chunk = "\n\n".join(current)
        if chunks and len(last_chunk) < MIN_CHUNK_CHARS:
            chunks[-1] = chunks[-1] + "\n\n" + last_chunk
        else:
            chunks.append(last_chunk)

    return chunks


def chunk_all():
    manifest_path = EXTRACTED_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    all_chunks = []
    chunk_counter = 0

    for entry in manifest:
        text_path = Path(entry["extracted_path"])
        text = text_path.read_text(encoding="utf-8")

        paragraphs = split_into_paragraphs(text)
        piece_texts = group_paragraphs_into_chunks(paragraphs)

        for piece_text in piece_texts:
            chunk_counter += 1
            all_chunks.append({
                "chunk_id": f"chunk_{chunk_counter:04d}",
                "text": piece_text,
                "source_id": entry["id"],
                "source_title": entry["title"],
                "source_url": entry["url"],
            })

        print(f"[OK] {entry['id']} -> {len(piece_texts)} chunks")

    out_path = CHUNKS_DIR / "chunks.json"
    out_path.write_text(json.dumps(all_chunks, indent=2), encoding="utf-8")
    print(f"\nTotal: {len(all_chunks)} chunks written to {out_path}")
    return all_chunks


if __name__ == "__main__":
    chunk_all()