"""Steps 4-6: RAG triage of support tickets (prompt version v2).

For every ticket:
  1. embed the ticket text                       (Gemini embeddings, 10 tickets per API call)
  2. retrieve the closest SOP chunks             (pgvector cosine search) and always add the
     "Escalation and priority" section of the best-matching SOP
  3. ask Gemini for category, priority, a confidence score and a suggested reply, using the
     category rules, priority definitions, a few invented examples and the SOP excerpts
  4. human-review rule (risk based): the ticket goes to the manual queue if its predicted priority
     or category is high-stakes (config: REVIEW_PRIORITIES, REVIEW_CATEGORIES), or if model
     confidence / knowledge-base similarity is low. The reasons are saved in review_reason.
  5. save everything to the ticket_triage table (one row per ticket, saved immediately)

Run examples:
    python src/triage_tickets.py --eval          the dev set in data/eval_to_label.csv
    python src/triage_tickets.py --test          the fresh test set in data/test_to_label.csv
    python src/triage_tickets.py --limit 20      the next 20 tickets that have no triage result yet
    python src/triage_tickets.py                 every ticket that has no triage result yet
    python src/triage_tickets.py --eval --redo   re-run (overwrite) results, e.g. after changing the prompt

The free tier allows about 500 triage calls per day, so only run the full set once the prompt is final.
"""
import argparse
import csv
import logging
from pathlib import Path

import psycopg2
from google.genai import errors
from pydantic import BaseModel, ValidationError

import config
from embed_kb import to_vector_literal
from llm_utils import embed_texts, generate_json
from search_kb import escalation_chunk, retrieve_by_vector
from taxonomy import (CATEGORIES, CATEGORY_RULES, COMPANY_CONTEXT, EXAMPLES, PRIORITIES,
                      PRIORITY_GUIDE, TAXONOMY_VERSION)

log = logging.getLogger("rag")
EVAL_FILES = {"dev": Path("data/eval_to_label.csv"), "test": Path("data/test_to_label.csv")}
EMBED_BATCH = 10

SYSTEM_PROMPT = (
    f"You are a support-ticket triage assistant. {COMPANY_CONTEXT} "
    "Follow the category rules and priority definitions you are given. Use the SOP excerpts for "
    "the procedure and the reply. If an SOP excerpt disagrees with the rules or the priority "
    "definitions, the rules and definitions win. Never invent order details, policies, amounts or "
    "time limits that are not in the SOP excerpts."
)


class TriageResult(BaseModel):
    """The JSON shape we ask Gemini to return (reasoning first, so the model thinks before it labels)."""
    reasoning: str
    category: str
    priority: str
    confidence: float
    suggested_reply: str


def build_prompt(ticket_text: str, chunks: list) -> str:
    """The instruction for one ticket: rules, examples, retrieved SOP excerpts and the output format."""
    categories = "\n".join(f"- {name}: {text}" for name, text in CATEGORIES.items())
    rules = "\n".join(f"{number}. {text}" for number, text in enumerate(CATEGORY_RULES, start=1))
    priorities = "\n".join(f"- {name}: {PRIORITY_GUIDE[name]}" for name in reversed(PRIORITIES))
    examples = "\n".join(f'- "{text}" -> {category} / {priority}' for text, category, priority in EXAMPLES)
    excerpts = "\n\n".join(f"[{number}] {chunk['content']}" for number, chunk in enumerate(chunks, start=1))
    return f'''Triage this customer support ticket.

TICKET:
"""
{ticket_text}
"""

CATEGORIES (choose exactly one, copy the name exactly):
{categories}

CATEGORY RULES (use them to break ties):
{rules}

PRIORITIES (choose exactly one, copy the name exactly):
{priorities}
Judge the customer's SITUATION, not their tone or wording.

EXAMPLES (invented tickets, category / priority):
{examples}

RELEVANT SOP EXCERPTS (procedure and reply guidance):
{excerpts}

INSTRUCTIONS:
- reasoning: one or two sentences on the customer's real situation and which rules apply.
- category: the single best category after applying the category rules.
- priority: apply the priority definitions to the situation.
- confidence: a number from 0 to 1 = how sure you are that BOTH category and priority are correct. Use below 0.6 when the ticket is vague, mixes several issues, or the rules do not clearly cover it.
- suggested_reply: a polite reply to the customer in 2 to 4 sentences that follows the SOP. Do not promise anything the SOP does not allow and do not invent order details.'''


def clean_result(result: TriageResult) -> TriageResult:
    """Make category and priority match our official names exactly; raise ValueError if they cannot."""
    categories = {name.lower(): name for name in CATEGORIES}
    priorities = {name.lower(): name for name in PRIORITIES}
    category = categories.get(" ".join(result.category.split()).lower())
    priority = priorities.get(" ".join(result.priority.split()).lower())
    if category is None or priority is None:
        raise ValueError(f"unknown category/priority: {result.category!r} / {result.priority!r}")
    result.category, result.priority = category, priority
    result.confidence = max(0.0, min(1.0, float(result.confidence)))
    return result


def review_reasons(category: str, priority: str, confidence: float, top_similarity: float) -> list:
    """The human-review rule. Returns the list of reasons (empty list = handled automatically)."""
    reasons = []
    if priority in config.REVIEW_PRIORITIES:
        reasons.append(f"predicted priority {priority}")
    if category in config.REVIEW_CATEGORIES:
        reasons.append(f"{category} is always reviewed")
    if confidence < config.CONFIDENCE_THRESHOLD:
        reasons.append("low model confidence")
    if top_similarity < config.MIN_RETRIEVAL_SIMILARITY:
        reasons.append("weak knowledge-base match")
    return reasons


def select_context(hits: list, connection) -> list:
    """Top-k chunks, plus the 'Escalation and priority' section of the best-matching SOP."""
    chunks = list(hits)
    if hits:
        extra = escalation_chunk(hits[0]["doc_title"], connection)
        if extra and extra["chunk_id"] not in {hit["chunk_id"] for hit in hits}:
            chunks.append(extra)
    return chunks


def triage_one(ticket_text: str, vector_literal: str, connection) -> dict:
    """Run the whole RAG flow for one ticket and return the row to save."""
    hits = retrieve_by_vector(vector_literal, config.TOP_K, connection)
    chunks = select_context(hits, connection)
    top_similarity = hits[0]["similarity"] if hits else 0.0

    result = None
    for attempt in range(2):                      # one retry if the model returns an unusable answer
        try:
            result = clean_result(generate_json(
                build_prompt(ticket_text, chunks), TriageResult, model=config.GEMINI_MODEL,
                system=SYSTEM_PROMPT, temperature=0.1))
            break
        except (ValidationError, ValueError) as error:
            log.warning("Unusable model answer (attempt %d): %s", attempt + 1, str(error)[:150])
    if result is None:
        raise ValueError("model failed to give a valid answer twice")

    reasons = review_reasons(result.category, result.priority, result.confidence, top_similarity)
    return {
        "category": result.category,
        "priority": result.priority,
        "suggested_reply": result.suggested_reply.strip(),
        "confidence": round(result.confidence, 3),
        "needs_review": bool(reasons),
        "review_reason": "; ".join(reasons),
        "source_chunk_ids": [chunk["chunk_id"] for chunk in chunks],
        "model_name": config.GEMINI_MODEL,
        "top_similarity": round(top_similarity, 3),
        "reasoning": result.reasoning.strip(),
        "prompt_version": TAXONOMY_VERSION,
    }


def fetch_tickets(connection, args) -> list:
    """Choose which tickets to triage."""
    conditions, params = [], []
    chosen_set = "dev" if args.eval else "test" if args.test else None
    if chosen_set:
        with EVAL_FILES[chosen_set].open(newline="", encoding="utf-8-sig") as file:
            ids = [int(row["ticket_id"]) for row in csv.DictReader(file)]
        conditions.append("t.ticket_id = ANY(%s)")
        params.append(ids)
    if not args.redo:
        conditions.append("NOT EXISTS (SELECT 1 FROM ticket_triage tr WHERE tr.ticket_id = t.ticket_id)")
    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    limit = f"LIMIT {int(args.limit)}" if args.limit else ""
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT t.ticket_id, t.ticket_text FROM tickets t {where} ORDER BY t.ticket_id {limit}", params)
        return cursor.fetchall()


def save_result(connection, ticket_id: int, row: dict) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            """INSERT INTO ticket_triage
                 (ticket_id, category, priority, suggested_reply, confidence, needs_review,
                  source_chunk_ids, model_name, top_similarity, reasoning, review_reason, prompt_version)
               VALUES (%(ticket_id)s, %(category)s, %(priority)s, %(suggested_reply)s, %(confidence)s,
                       %(needs_review)s, %(source_chunk_ids)s, %(model_name)s, %(top_similarity)s, %(reasoning)s,
                       %(review_reason)s, %(prompt_version)s)
               ON CONFLICT (ticket_id) DO UPDATE SET
                 category = EXCLUDED.category, priority = EXCLUDED.priority,
                 suggested_reply = EXCLUDED.suggested_reply, confidence = EXCLUDED.confidence,
                 needs_review = EXCLUDED.needs_review, source_chunk_ids = EXCLUDED.source_chunk_ids,
                 model_name = EXCLUDED.model_name, top_similarity = EXCLUDED.top_similarity,
                 reasoning = EXCLUDED.reasoning, review_reason = EXCLUDED.review_reason,
                 prompt_version = EXCLUDED.prompt_version, triaged_at = now()""",
            {"ticket_id": ticket_id, **row})
    connection.commit()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s", datefmt="%H:%M:%S")
    parser = argparse.ArgumentParser()
    parser.add_argument("--eval", action="store_true", help="the dev set listed in data/eval_to_label.csv")
    parser.add_argument("--test", action="store_true", help="the fresh test set listed in data/test_to_label.csv")
    parser.add_argument("--limit", type=int, help="triage at most this many tickets")
    parser.add_argument("--redo", action="store_true", help="also re-triage tickets that already have a result")
    args = parser.parse_args()
    if args.eval and args.test:
        raise SystemExit("Choose either --eval or --test, not both.")
    if not config.GEMINI_MODEL:
        raise RuntimeError("Set GEMINI_MODEL in your .env file first.")

    connection = psycopg2.connect(**config.DB_CONFIG)
    tickets = fetch_tickets(connection, args)
    log.info("%d tickets to triage (model: %s, prompt %s). Review if priority in %s, category in %s, "
             "confidence < %.2f or similarity < %.2f", len(tickets), config.GEMINI_MODEL, TAXONOMY_VERSION,
             sorted(config.REVIEW_PRIORITIES), sorted(config.REVIEW_CATEGORIES),
             config.CONFIDENCE_THRESHOLD, config.MIN_RETRIEVAL_SIMILARITY)

    done = flagged = 0
    try:
        for start in range(0, len(tickets), EMBED_BATCH):
            batch = tickets[start:start + EMBED_BATCH]
            vectors = embed_texts([text for _, text in batch], task_type="RETRIEVAL_QUERY")
            for (ticket_id, text), vector in zip(batch, vectors):
                try:
                    row = triage_one(text, to_vector_literal(vector), connection)
                except ValueError as error:
                    log.warning("Ticket %d skipped: %s", ticket_id, error)
                    continue
                save_result(connection, ticket_id, row)
                done += 1
                flagged += row["needs_review"]
                log.info("Ticket %4d | %-20s | %-6s | conf %.2f | sim %.2f | %s", ticket_id, row["category"],
                         row["priority"], row["confidence"], row["top_similarity"],
                         "REVIEW" if row["needs_review"] else "auto")
    except errors.APIError as error:
        log.error("Gemini stopped us (%s). Everything done so far is saved: run again later.", str(error)[:200])
    finally:
        connection.close()

    log.info("Finished: %d triaged, %d sent to the human review queue (%.0f%%).",
             done, flagged, 100 * flagged / done if done else 0)


if __name__ == "__main__":
    main()
