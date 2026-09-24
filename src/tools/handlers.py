"""The two tools the model may request. The application runs them."""

from rag.retrieve import retrieve

from tools.case_store import blocked_topic, create_draft

MAX_TOP_K = 3


def retrieve_documents(arguments: dict) -> dict:
    query = str(arguments.get("query") or "").strip()
    if not query:
        return {
            "status": "error",
            "chunks": [],
            "retrieved_count": 0,
            "message": "query is required",
        }
    if blocked_topic(query):
        return {
            "status": "error",
            "chunks": [],
            "retrieved_count": 0,
            "message": "Admissions, grading, and disciplinary questions are declined.",
        }

    try:
        top_k = int(arguments.get("top_k", MAX_TOP_K))
    except (TypeError, ValueError):
        top_k = MAX_TOP_K
    top_k = min(MAX_TOP_K, max(1, top_k))

    try:
        found = retrieve(query, top_k=top_k)
    except Exception:
        return {
            "status": "error",
            "chunks": [],
            "retrieved_count": 0,
            "message": "The document index is unavailable.",
        }

    chunks = []
    for item in found:
        title = item.get("source_title")
        url = item.get("source_url")
        if not title or not url:
            continue
        chunks.append({
            "chunk_id": item.get("chunk_id", ""),
            "text": item.get("text", ""),
            "source_title": title,
            "source_url": url,
            "similarity_score": item.get("similarity", 0),
        })

    if not chunks:
        return {"status": "no_match", "chunks": [], "retrieved_count": 0}
    return {"status": "ok", "chunks": chunks, "retrieved_count": len(chunks)}


def create_support_case(arguments: dict, session_id: str) -> dict:
    supplied = dict(arguments)
    supplied.pop("session_id", None)
    return create_draft(supplied, session_id)
