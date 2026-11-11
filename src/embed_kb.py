"""Step 3b: split the SOP documents into chunks, embed them and store the vectors in pgvector.

Chunking rule: every "## section" of an SOP becomes one chunk (Purpose, Steps, Escalation and
priority ...), prefixed with the document title so the chunk makes sense on its own. Very small
sections are merged with their neighbour and very long ones are split at paragraph boundaries.

Run:  python src/embed_kb.py        (safe to re-run: chunks are updated, not duplicated)
"""
import logging
import re
from pathlib import Path

import psycopg2
from psycopg2.extras import execute_values

import config
from llm_utils import embed_texts

log = logging.getLogger("rag")
SOP_DIR = Path("data/sops")
MIN_CHARS = 250     # sections shorter than this are merged into the previous chunk
MAX_CHARS = 1500    # chunks longer than this are split


def split_long(text: str) -> list:
    """Split an over-long chunk at paragraph boundaries."""
    if len(text) <= MAX_CHARS:
        return [text]
    parts, current = [], ""
    for paragraph in re.split(r"\n\s*\n|\n(?=\d+\.\s)", text):
        if current and len(current) + len(paragraph) > MAX_CHARS:
            parts.append(current.strip())
            current = ""
        current += paragraph + "\n\n"
    if current.strip():
        parts.append(current.strip())
    return parts


def chunk_document(title: str, markdown: str) -> list:
    """Turn one SOP into a list of chunk texts."""
    sections = re.split(r"(?m)^##\s+", markdown)[1:]       # text before the first '##' is just the title
    chunks = []
    for section in sections:
        heading, _, body = section.partition("\n")
        if body.strip():
            chunks.append(f"{title} - {heading.strip()}\n{body.strip()}")
    if not chunks:                                          # no '##' headings: keep the whole text
        chunks = [f"{title}\n{markdown.strip()}"]
    merged = []
    for chunk in chunks:
        if merged and len(chunk) < MIN_CHARS:
            merged[-1] += "\n\n" + chunk
        else:
            merged.append(chunk)
    return [piece for chunk in merged for piece in split_long(chunk)]


def title_of(markdown: str, fallback: str) -> str:
    match = re.match(r"\s*#\s+(.+)", markdown)
    return match.group(1).strip() if match else fallback


def to_vector_literal(values: list) -> str:
    """pgvector accepts vectors written as text, e.g. '[0.1,0.2,0.3]'."""
    return "[" + ",".join(f"{value:.7f}" for value in values) + "]"


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s", datefmt="%H:%M:%S")
    files = sorted(SOP_DIR.glob("*.md"))
    if not files:
        raise RuntimeError(f"No SOP files in {SOP_DIR}. Run generate_kb.py first.")

    records = []    # (doc_title, chunk_index, content)
    for path in files:
        markdown = path.read_text(encoding="utf-8")
        title = title_of(markdown, path.stem)
        for index, chunk in enumerate(chunk_document(title, markdown)):
            records.append((title, index, chunk))
    log.info("%d documents -> %d chunks. Embedding with %s (%d dimensions)...",
             len(files), len(records), config.EMBED_MODEL, config.EMBED_DIM)

    vectors = embed_texts([content for _, _, content in records], task_type="RETRIEVAL_DOCUMENT")
    rows = [(title, index, content, to_vector_literal(vector))
            for (title, index, content), vector in zip(records, vectors)]

    connection = psycopg2.connect(**config.DB_CONFIG)
    with connection, connection.cursor() as cursor:
        execute_values(
            cursor,
            """INSERT INTO kb_chunks (doc_title, chunk_index, content, embedding) VALUES %s
               ON CONFLICT (doc_title, chunk_index)
               DO UPDATE SET content = EXCLUDED.content, embedding = EXCLUDED.embedding""",
            rows, template="(%s, %s, %s, %s::vector)")
        cursor.execute("SELECT COUNT(*), COUNT(DISTINCT doc_title) FROM kb_chunks")
        count, documents = cursor.fetchone()
    connection.close()
    log.info("kb_chunks now holds %d chunks from %d documents.", count, documents)


if __name__ == "__main__":
    main()
