"""
ingest.py — Milestone 2/3: load, clean, and chunk the Unofficial Guide corpus.

Domain: student reviews of Computer Science professors at Binghamton University.

Pipeline stages implemented here (see planning.md > Architecture):
    1. Document ingestion  -> load_documents()
    2. Cleaning            -> clean_text()
    3. Chunking            -> chunk_documents()   (review-aware, per planning.md)

Run:
    python ingest.py

Output:
    - prints a cleaning self-test, 5 representative chunks, and the total chunk count
    - writes all chunks (text + metadata) to chunks.json for Milestone 4 (embedding)
"""

from __future__ import annotations

import html
import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

# --- Configuration (mirrors planning.md > Chunking Strategy) -----------------
DOCUMENTS_DIR = Path(__file__).parent / "documents"
OUTPUT_FILE = Path(__file__).parent / "chunks.json"
MAX_CHARS = 512          # max characters per chunk
OVERLAP = 50             # character overlap, applied ONLY when splitting a long record
RECORD_DELIM = re.compile(r"^=== (REVIEW|POST) ===\s*$", re.MULTILINE)

# Boilerplate lines that show up on saved review pages but carry no domain content.
# (Kept conservative — we never strip review text, only known chrome.)
BOILERPLATE_PATTERNS = [
    re.compile(r"^\s*(Helpful|Not Helpful|Report|Share|Compare)\s*$", re.IGNORECASE),
    re.compile(r"^\s*Rate (this )?Professor\s*$", re.IGNORECASE),
    re.compile(r"^\s*Add a (rating|review)\s*$", re.IGNORECASE),
    re.compile(r"^\s*\d+\s+(helpful|unhelpful)\s*$", re.IGNORECASE),
    re.compile(r"^\s*(Read more|Show more|Load more)\s*$", re.IGNORECASE),
]


@dataclass
class Chunk:
    text: str
    metadata: dict = field(default_factory=dict)


# --- Stage 1: Ingestion ------------------------------------------------------
def load_documents(directory: Path = DOCUMENTS_DIR) -> list[tuple[str, str]]:
    """Load every .txt/.md file in `directory`. Returns (filename, raw_text)."""
    docs = []
    for path in sorted(directory.glob("*")):
        if path.suffix.lower() in {".txt", ".md"} and path.name != ".gitkeep":
            docs.append((path.name, path.read_text(encoding="utf-8")))
    if not docs:
        raise SystemExit(f"No documents found in {directory}. Add source files first.")
    return docs


# --- Stage 2: Cleaning -------------------------------------------------------
def clean_text(raw: str) -> str:
    """Remove HTML tags/entities and known boilerplate; normalize whitespace.

    Our corpus was extracted as text, so the HTML path is mostly a safety net for
    any pages saved as raw .html later — but it runs on every document so cleaning
    is reproducible regardless of how a source was captured.
    """
    text = html.unescape(raw)                 # &amp; -> &, &#39; -> ', &nbsp; -> space
    text = re.sub(r"<[^>]+>", "", text)        # strip HTML tags
    text = text.replace(" ", " ")         # stray non-breaking spaces

    kept_lines = []
    for line in text.splitlines():
        if any(p.match(line) for p in BOILERPLATE_PATTERNS):
            continue
        kept_lines.append(line.rstrip())
    text = "\n".join(kept_lines)

    text = re.sub(r"\n{3,}", "\n\n", text)     # collapse runs of blank lines
    return text.strip()


# --- Header / record parsing -------------------------------------------------
def _parse_kv_block(block: str) -> dict:
    """Parse 'KEY: value' header lines into a dict (lowercased keys)."""
    meta = {}
    for line in block.splitlines():
        m = re.match(r"^([A-Z][A-Z _]+):\s*(.*)$", line)
        if m:
            meta[m.group(1).strip().lower().replace(" ", "_")] = m.group(2).strip()
    return meta


def _record_body_and_meta(body: str) -> tuple[str, dict]:
    """Split a record into its sub-field metadata and free-text body."""
    field_keys = {"course", "date", "quality", "difficulty", "tags", "author",
                  "grade", "attendance"}
    meta, body_lines = {}, []
    for line in body.splitlines():
        m = re.match(r"^([A-Za-z][A-Za-z _]+):\s*(.*)$", line)
        if m and m.group(1).strip().lower().replace(" ", "_") in field_keys:
            meta[m.group(1).strip().lower().replace(" ", "_")] = m.group(2).strip()
        else:
            body_lines.append(line)
    return "\n".join(body_lines).strip(), meta


# --- Stage 3: Chunking (review-aware) ---------------------------------------
def _split_with_overlap(text: str, size: int = MAX_CHARS, overlap: int = OVERLAP) -> list[str]:
    """Sliding-window split for records longer than `size`, breaking on whitespace."""
    if len(text) <= size:
        return [text]
    chunks, start = [], 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):
            ws = text.rfind(" ", start, end)
            if ws > start:
                end = ws
        chunks.append(text[start:end].strip())
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    return [c for c in chunks if c]


def _context_prefix(doc_meta: dict, rec_meta: dict, kind: str) -> str:
    """Build a standalone context header so a chunk is interpretable on its own
    (addresses planning.md Anticipated Challenge #2: lost professor/course context)."""
    prof = doc_meta.get("professor") or doc_meta.get("title", "Unknown")
    if kind == "POST":
        author = rec_meta.get("author", "anonymous")
        date = rec_meta.get("date", "")
        return f"Binghamton CS discussion (College Confidential), post by {author} ({date}):"
    course = rec_meta.get("course", "")
    date = rec_meta.get("date", "")
    quality = rec_meta.get("quality", "")
    difficulty = rec_meta.get("difficulty", "")
    bits = [f"Professor {prof}"]
    if course:
        bits.append(course)
    head = " — ".join(bits)
    rating = ""
    if quality or difficulty:
        rating = f" Student rating: quality {quality or 'n/a'}, difficulty {difficulty or 'n/a'}."
    return f"{head} (RateMyProfessors review, {date}).{rating}"


def chunk_documents(docs: list[tuple[str, str]]) -> list[Chunk]:
    """Clean each document, split into atomic records, and emit chunks w/ metadata."""
    all_chunks: list[Chunk] = []

    for filename, raw in docs:
        text = clean_text(raw)
        parts = RECORD_DELIM.split(text)
        header_block = parts[0]
        doc_meta = _parse_kv_block(header_block)
        base_meta = {
            "source_file": filename,
            "source_url": doc_meta.get("source_url", ""),
            "source_type": doc_meta.get("source_type", ""),
            "professor": doc_meta.get("professor", ""),
        }

        # The profile-summary line in the header becomes its own chunk (carries
        # the aggregate rating / would-take-again / difficulty facts).
        m = re.search(r"PROFILE SUMMARY:\s*(.+)", header_block)
        if m:
            all_chunks.append(Chunk(
                text=m.group(1).strip(),
                metadata={**base_meta, "record_type": "profile_summary"},
            ))

        # parts = [header, KIND, body, KIND, body, ...]
        for i in range(1, len(parts), 2):
            kind, body = parts[i], parts[i + 1]
            body_text, rec_meta = _record_body_and_meta(body)
            if not body_text:
                continue
            prefix = _context_prefix(doc_meta, rec_meta, kind)
            full = f"{prefix}\n{body_text}"

            pieces = _split_with_overlap(full)
            for j, piece in enumerate(pieces):
                meta = {
                    **base_meta,
                    "record_type": "review" if kind == "REVIEW" else "forum_post",
                    "course": rec_meta.get("course", ""),
                    "date": rec_meta.get("date", ""),
                    "author": rec_meta.get("author", ""),
                }
                if len(pieces) > 1:
                    meta["part"] = f"{j + 1}/{len(pieces)}"
                all_chunks.append(Chunk(text=piece, metadata=meta))

    return all_chunks


# --- Demonstrations / driver -------------------------------------------------
def _cleaning_self_test() -> None:
    sample = '<div class="review-body">Professor Smith&#39;s exams are&nbsp;hard.</div>\nHelpful\n0 helpful'
    print("Cleaning self-test")
    print("  RAW    :", repr(sample))
    print("  CLEANED:", repr(clean_text(sample)))
    print()


def main() -> None:
    # Print UTF-8 cleanly on Windows consoles (review text contains em-dashes etc.).
    try:
        import sys
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    docs = load_documents()
    print(f"Loaded {len(docs)} documents from {DOCUMENTS_DIR}\n")

    _cleaning_self_test()

    chunks = chunk_documents(docs)

    # Save for Milestone 4
    OUTPUT_FILE.write_text(
        json.dumps([asdict(c) for c in chunks], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # Inspect 5 representative chunks (varied record types and professors).
    print("=" * 70)
    print("5 REPRESENTATIVE CHUNKS")
    print("=" * 70)
    sample_idx = _pick_representative(chunks, 5)
    for n, idx in enumerate(sample_idx, 1):
        c = chunks[idx]
        print(f"\n--- Chunk {n}  [source: {c.metadata['source_file']}  "
              f"type: {c.metadata['record_type']}  len: {len(c.text)}] ---")
        print(c.text)

    # Length distribution + total count
    lengths = [len(c.text) for c in chunks]
    print("\n" + "=" * 70)
    print(f"TOTAL CHUNKS: {len(chunks)}")
    print(f"  chunk length  min/mean/max: "
          f"{min(lengths)} / {sum(lengths)//len(lengths)} / {max(lengths)} chars")
    print(f"  records split across >1 chunk: "
          f"{sum(1 for c in chunks if 'part' in c.metadata)}")
    print(f"  written to: {OUTPUT_FILE.name}")
    print("=" * 70)


def _pick_representative(chunks: list[Chunk], k: int) -> list[int]:
    """Pick k chunks that span record types and distinct source files, favoring
    substantive (non-trivial length) chunks so the inspection is illustrative."""
    by_type: dict[str, list[int]] = {}
    for i, c in enumerate(chunks):
        by_type.setdefault(c.metadata["record_type"], []).append(i)

    # Target mix: 3 reviews (distinct professors), 1 profile summary, 1 forum post.
    plan = ["review", "review", "review", "profile_summary", "forum_post"]
    chosen, used_files = [], set()
    for want in plan:
        for i in by_type.get(want, []):
            f = chunks[i].metadata["source_file"]
            if i in chosen or f in used_files or len(chunks[i].text) < 150:
                continue
            chosen.append(i)
            used_files.add(f)
            break
    # Backfill if any slot couldn't be satisfied.
    for i in range(len(chunks)):
        if len(chosen) >= k:
            break
        if i not in chosen:
            chosen.append(i)
    return chosen[:k]


if __name__ == "__main__":
    main()
