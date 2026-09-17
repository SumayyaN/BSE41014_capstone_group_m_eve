import os
from google import genai
from dotenv import load_dotenv
from pathlib import Path

from rag.retrieve import retrieve

env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"

# Versions that have RAG wired in. v1.0 and v1.1 stay exactly as documented
# (no retrieval, no citations) so they remain honest baselines for comparison;
# only v1.2+ actually uses the corpus.
RAG_ENABLED_VERSIONS = {"v1.2"}


def load_prompt(version: str = "v1.0") -> str:
    """Load system prompt from file."""
    prompt_path = PROMPTS_DIR / f"{version}_baseline.txt"
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt not found: {prompt_path}")
    return prompt_path.read_text(encoding="utf-8").strip()


def build_context_block(retrieved_chunks: list[dict]) -> str:
    """Format retrieved chunks into a labeled context block for the model,
    so each piece of information is traceable to its source document."""
    if not retrieved_chunks:
        return ""

    parts = []
    for chunk in retrieved_chunks:
        parts.append(f"[Source: {chunk['source_title']}]\n{chunk['text']}")
    return "\n\n---\n\n".join(parts)


def ask_llm(question: str, prompt_version: str = "v1.0") -> str:
    """Send a question to Gemini and return the response.

    For RAG-enabled prompt versions, retrieves relevant chunks from the
    corpus first and injects them as labeled context, so the model answers
    from real documents and can cite its source - rather than from its own
    general/training knowledge, which is what caused the fabricated
    ACMIS/DICTS details found in Week 2 testing (see docs/evaluation).
    """
    system_prompt = load_prompt(prompt_version)

    if prompt_version in RAG_ENABLED_VERSIONS:
        retrieved_chunks = retrieve(question)
        context_block = build_context_block(retrieved_chunks)

        if context_block:
            model_input = (
                f"Context from official Makerere documents:\n\n{context_block}\n\n"
                f"Student question: {question}\n\n"
                f"Answer using only the context above, and name the source document you used."
            )
        else:
            # No chunk cleared the similarity threshold - be explicit that
            # there is no relevant context, so the model gives the honest
            # fallback rather than answering from its own general knowledge.
            model_input = (
                f"No relevant context was found in the official documents for this question.\n\n"
                f"Student question: {question}\n\n"
                f"State clearly that you do not have confirmed information on this, per your instructions."
            )
    else:
        model_input = question

    interaction = client.interactions.create(
        model="gemini-3.6-flash",
        input=model_input,
        system_instruction=system_prompt,
        generation_config={
            "thinking_level": "low"
        }
    )

    return interaction.output_text