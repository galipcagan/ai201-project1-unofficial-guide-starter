"""
query.py — Milestone 5: grounded generation.

Pipeline stage 5 (see planning.md > Architecture):
    Retrieval (retrieval.retrieve) -> build grounded prompt -> Groq LLM -> answer + sources

Grounding is enforced THREE ways, not just by asking nicely:
  1. Structural relevance gate: chunks whose cosine distance exceeds MAX_DISTANCE are
     dropped. If nothing clears the gate, we return the refusal WITHOUT calling the LLM
     (so an out-of-scope question can't be answered from training data).
  2. System prompt: the model is instructed to use ONLY the provided context and to
     return a fixed refusal string when the context is insufficient.
  3. Programmatic attribution: the `sources` list is built from the metadata of the
     chunks we actually passed in — it is never left to the LLM to invent.

Run:
    python query.py        # end-to-end test on grounded + out-of-scope queries
"""

from __future__ import annotations

import os

from dotenv import load_dotenv
from groq import Groq

from retrieval import retrieve, DEFAULT_K

load_dotenv()

LLM_MODEL = "llama-3.3-70b-versatile"
MAX_DISTANCE = 0.60        # cosine-distance ceiling for a chunk to count as relevant
REFUSAL = "I don't have enough information on that."

SYSTEM_PROMPT = """You are the Unofficial Guide to Binghamton University Computer Science professors. \
You answer questions using ONLY the student-review excerpts provided in the CONTEXT block.

Rules you must follow exactly:
1. Use ONLY information found in the CONTEXT. Do NOT use any outside or general knowledge, \
and do NOT guess or infer beyond what the excerpts say.
2. If the CONTEXT does not contain enough information to answer the question, reply with \
EXACTLY this sentence and nothing else: "I don't have enough information on that."
3. Cite the excerpts you used by their bracket number, e.g. [1], [3], placed right after \
the claim they support.
4. When reviews disagree, report the disagreement (e.g. "some reviewers say... while others say...") \
rather than picking one side.
5. Keep the answer concise and specific to what students actually wrote."""

_client: Groq | None = None


def _groq() -> Groq:
    global _client
    if _client is None:
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key or api_key == "your_key_here":
            raise SystemExit("GROQ_API_KEY is missing or still the placeholder in .env")
        _client = Groq(api_key=api_key)
    return _client


def _format_context(chunks: list[dict]) -> str:
    """Render retrieved chunks as numbered, source-labeled context blocks."""
    blocks = []
    for i, c in enumerate(chunks, 1):
        blocks.append(f"[{i}] (source: {c['source_file']})\n{c['text']}")
    return "\n\n".join(blocks)


def _source_list(chunks: list[dict]) -> list[str]:
    """Build the attribution list programmatically from retrieved metadata (dedup, ordered)."""
    seen, sources = set(), []
    for c in chunks:
        key = c["source_file"]
        if key in seen:
            continue
        seen.add(key)
        url = c.get("source_url", "")
        sources.append(f"{key}" + (f" ({url})" if url else ""))
    return sources


def ask(question: str, k: int = DEFAULT_K, max_distance: float = MAX_DISTANCE) -> dict:
    """Answer `question` grounded strictly in retrieved review chunks.

    Returns {answer, sources, chunks, grounded}:
        answer   - the model's text (or the fixed refusal)
        sources  - list of source documents the answer is attributed to
        chunks   - the relevant chunks that were passed as context
        grounded - False when the relevance gate refused before calling the LLM
    """
    retrieved = retrieve(question, k=k)
    relevant = [c for c in retrieved if c["distance"] <= max_distance]

    # (1) Structural gate: no sufficiently-relevant chunk -> refuse without the LLM.
    if not relevant:
        return {"answer": REFUSAL, "sources": [], "chunks": [], "grounded": False}

    context = _format_context(relevant)
    user_msg = (
        f"CONTEXT:\n{context}\n\n"
        f"QUESTION: {question}\n\n"
        "Answer using only the CONTEXT above, following all the rules."
    )

    completion = _groq().chat.completions.create(
        model=LLM_MODEL,
        temperature=0.0,  # deterministic, reduces drift away from the context
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
    )
    answer = completion.choices[0].message.content.strip()

    # (3) If the model still refused, don't attach sources.
    if answer.rstrip(".") == REFUSAL.rstrip("."):
        return {"answer": REFUSAL, "sources": [], "chunks": relevant, "grounded": False}

    return {
        "answer": answer,
        "sources": _source_list(relevant),
        "chunks": relevant,
        "grounded": True,
    }


# --- End-to-end test ---------------------------------------------------------
TEST_QUERIES = [
    "What do students say about Patrick Madden's lectures and exams?",   # grounded
    "Is Thomas Bartenstein a good professor to take for CS 220?",        # grounded
    "What are the best off-campus apartments near Binghamton?",          # out-of-scope
]


def _demo() -> None:
    try:
        import sys
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    for q in TEST_QUERIES:
        print("=" * 78)
        print(f"Q: {q}")
        print("-" * 78)
        result = ask(q)
        print(result["answer"])
        if result["sources"]:
            print("\nRetrieved from:")
            for s in result["sources"]:
                print(f"  • {s}")
        else:
            print(f"\n(grounded={result['grounded']}, no sources attached)")
        print()


if __name__ == "__main__":
    _demo()
