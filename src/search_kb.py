"""Retrieval: find the knowledge-base chunks most similar to a piece of text.

`retrieve()`, `retrieve_by_vector()` and `escalation_chunk()` are used by the triage pipeline.

Try it:
    python src/search_kb.py "I was charged twice for the same order"
    python src/search_kb.py            (runs a few sample queries)
"""
import sys

import psycopg2

import config
from embed_kb import to_vector_literal
from llm_utils import embed_texts

SAMPLE_QUERIES = [
    "I was charged twice for the same order",
    "my package says delivered but I never got it",
    "someone logged into my account and placed orders I did not make",
    "how long does my refund take to reach my card",
    "the checkout button does nothing and the page freezes",
    "my blender arrived with a cracked jug",
]


def retrieve_by_vector(vector_literal: str, k: int = 3, connection=None) -> list:
    """Return the k closest chunks to an already-embedded query (vector written as text).

    Each result is a dict: chunk_id, doc_title, content, similarity (cosine, higher = closer).
    Pass an open `connection` to reuse it, otherwise one is opened and closed here.
    """
    own_connection = connection is None
    if own_connection:
        connection = psycopg2.connect(**config.DB_CONFIG)
    with connection.cursor() as cursor:
        # `<=>` is cosine distance in pgvector; similarity = 1 - distance.
        cursor.execute(
            """SELECT chunk_id, doc_title, content, 1 - (embedding <=> %s::vector) AS similarity
               FROM kb_chunks ORDER BY embedding <=> %s::vector LIMIT %s""",
            (vector_literal, vector_literal, k))
        rows = cursor.fetchall()
    if own_connection:
        connection.close()
    return [{"chunk_id": r[0], "doc_title": r[1], "content": r[2], "similarity": float(r[3])} for r in rows]


def retrieve(query: str, k: int = 3, connection=None) -> list:
    """Embed a text query and return the k closest knowledge-base chunks."""
    vector = embed_texts([query], task_type="RETRIEVAL_QUERY")[0]
    return retrieve_by_vector(to_vector_literal(vector), k, connection)


def escalation_chunk(doc_title: str, connection) -> dict | None:
    """The 'Escalation and priority' section of a document (what decides a ticket's priority)."""
    with connection.cursor() as cursor:
        cursor.execute(
            """SELECT chunk_id, doc_title, content FROM kb_chunks
               WHERE doc_title = %s AND content ILIKE %s ORDER BY chunk_index LIMIT 1""",
            (doc_title, "%Escalation and priority%"))
        row = cursor.fetchone()
    return {"chunk_id": row[0], "doc_title": row[1], "content": row[2], "similarity": None} if row else None


def main() -> None:
    queries = [" ".join(sys.argv[1:])] if len(sys.argv) > 1 else SAMPLE_QUERIES
    for query in queries:
        print(f"\nQUERY: {query}")
        for rank, hit in enumerate(retrieve(query), start=1):
            first_line = hit["content"].splitlines()[0]
            print(f"  {rank}. [{hit['similarity']:.3f}] {first_line}")


if __name__ == "__main__":
    main()
