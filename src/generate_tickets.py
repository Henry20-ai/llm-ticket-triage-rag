"""Step 1: generate ~420 realistic synthetic support tickets with Gemini + Faker.

How it works
  * A deterministic PLAN decides, for every batch of 10 tickets, the category, the priority
    of each ticket, the writing style, and fake customer details (Faker).
  * Gemini only writes the ticket text. We, not the model, decide category and priority,
    so the data has a controlled, balanced mix.
  * Every finished batch is saved immediately to data/tickets_raw.jsonl. If the free daily
    quota runs out or the script stops, run it again: finished batches are skipped.
  * At the end, timestamps are added (created_at / resolved_at, with realistic resolution
    times per priority) and everything is written to data/tickets.csv.

Run:  python src/generate_tickets.py
"""
import csv
import json
import logging
import random
from datetime import datetime, timedelta
from pathlib import Path

from faker import Faker
from google.genai import errors
from pydantic import BaseModel

import config
from llm_utils import generate_json
from taxonomy import (CATEGORIES, COMPANY_CONTEXT, PRIORITIES, PRIORITY_GUIDE, PRODUCTS,
                      STYLES, TICKET_PLAN)

log = logging.getLogger("rag")

DATA_DIR = Path("data")
RAW_FILE = DATA_DIR / "tickets_raw.jsonl"
OUT_FILE = DATA_DIR / "tickets.csv"
BATCH_SIZE = 10
SEED = 42

# Typical hours to resolve a ticket, by priority (min, max).
RESOLUTION_HOURS = {"Urgent": (0.5, 8), "High": (2, 36), "Medium": (8, 96), "Low": (24, 240)}
UNRESOLVED_SHARE = 0.06   # about 6% of tickets are still open


class TicketBatch(BaseModel):
    """The JSON shape we ask Gemini to return."""
    tickets: list[str]


def build_plan() -> list[dict]:
    """Decide every batch up front (same plan every run, because the seed is fixed)."""
    rng = random.Random(SEED)
    Faker.seed(SEED)
    fake = Faker()
    batches = []
    for category, (total, weights) in TICKET_PLAN.items():
        for index in range(total // BATCH_SIZE):
            priorities = rng.choices(PRIORITIES, weights=weights, k=BATCH_SIZE)
            items = [{
                "priority": priority,
                "style": rng.choice(STYLES),
                "customer": fake.name(),
                "order_id": f"BC-{rng.randint(100000, 999999)}",
                "product": rng.choice(PRODUCTS),
            } for priority in priorities]
            batches.append({"batch_id": f"{category}|{index}", "category": category, "items": items})
    # Shuffle so that a partial run (quota stop) is still a balanced mix of categories.
    rng.shuffle(batches)
    return batches


def build_prompt(batch: dict) -> str:
    """The instruction sent to Gemini for one batch."""
    lines = [
        f"{number}. priority: {item['priority']} | style: {item['style']} | customer: {item['customer']} "
        f"| order: {item['order_id']} | product: {item['product']}"
        for number, item in enumerate(batch["items"], start=1)
    ]
    guide = "\n".join(f"- {name}: {text}" for name, text in PRIORITY_GUIDE.items())
    category = batch["category"]
    return f"""Write {len(batch['items'])} different customer support tickets.
All tickets belong to this category: {category} - {CATEGORIES[category]}

Priority definitions (the situation in the ticket must clearly fit its priority):
{guide}

Write one ticket per numbered line below, in the same order, matching its priority and style:
{chr(10).join(lines)}

Rules:
- Each ticket is exactly what the customer typed into the support form: 1 to 6 sentences, no subject line, no signature template.
- Use the customer's name, order number and product only where a real customer would. Not in every ticket.
- Do not write the category name or a label such as "Priority: High". Show urgency through the situation instead.
- Every ticket must be clearly different in wording and situation.
Return JSON: {{"tickets": [...]}} containing exactly {len(batch['items'])} strings."""


def load_finished_batches() -> dict:
    """Read batches that were already generated in earlier runs."""
    finished = {}
    if RAW_FILE.exists():
        for line in RAW_FILE.read_text(encoding="utf-8").splitlines():
            if line.strip():
                record = json.loads(line)
                finished[record["batch_id"]] = record
    return finished


def generate_missing_batches(plan: list[dict], finished: dict) -> None:
    """Call Gemini for every batch not yet done. Stops cleanly if the quota is exhausted."""
    pending = [batch for batch in plan if batch["batch_id"] not in finished]
    log.info("%d batches planned, %d already done, %d to generate (model: %s)",
             len(plan), len(finished), len(pending), config.DATA_GEN_MODEL)
    if pending and not config.DATA_GEN_MODEL:
        raise RuntimeError("Set GEMINI_MODEL (or DATA_GEN_MODEL) in your .env file first.")

    for number, batch in enumerate(pending, start=1):
        try:
            result = generate_json(
                build_prompt(batch), TicketBatch, model=config.DATA_GEN_MODEL,
                system=f"You write realistic customer support messages. {COMPANY_CONTEXT}",
                temperature=1.0)
        except errors.APIError as error:
            log.error("Gemini stopped us (%s). Progress is saved: run the script again later.", error)
            return
        texts = [text.strip() for text in result.tickets if text.strip()]
        if len(texts) != len(batch["items"]):
            log.warning("Batch %s returned %d tickets instead of %d, skipping (it will retry next run)",
                        batch["batch_id"], len(texts), len(batch["items"]))
            continue
        record = {
            "batch_id": batch["batch_id"],
            "category": batch["category"],
            "tickets": [{"text": text, "priority": item["priority"]}
                        for text, item in zip(texts, batch["items"])],
        }
        with RAW_FILE.open("a", encoding="utf-8") as file:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")
        log.info("Batch %d/%d done: %s", number, len(pending), batch["batch_id"])


def build_csv(finished: dict) -> int:
    """Add realistic timestamps and write data/tickets.csv. Returns the number of tickets."""
    rng = random.Random(SEED + 1)
    now = datetime.now().replace(microsecond=0)
    seen_texts = set()
    rows = []
    for record in finished.values():
        for ticket in record["tickets"]:
            key = " ".join(ticket["text"].lower().split())
            if key in seen_texts:      # drop exact duplicates
                continue
            seen_texts.add(key)
            # Created sometime in the last 90 days, mostly during working hours.
            created = now - timedelta(days=rng.randint(0, 89))
            created = created.replace(hour=rng.choice([8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 20]),
                                      minute=rng.randint(0, 59), second=rng.randint(0, 59))
            low, high = RESOLUTION_HOURS[ticket["priority"]]
            resolved = created + timedelta(hours=rng.uniform(low, high))
            if rng.random() < UNRESOLVED_SHARE or resolved > now:
                resolved = None        # still open
            rows.append({
                "ticket_text": ticket["text"],
                "generated_category": record["category"],
                "generated_priority": ticket["priority"],
                "created_at": created.isoformat(sep=" "),
                "resolved_at": resolved.replace(microsecond=0).isoformat(sep=" ") if resolved else "",
            })
    rows.sort(key=lambda row: row["created_at"])
    with OUT_FILE.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s", datefmt="%H:%M:%S")
    DATA_DIR.mkdir(exist_ok=True)

    plan = build_plan()
    finished = load_finished_batches()
    generate_missing_batches(plan, finished)
    finished = load_finished_batches()

    if not finished:
        log.error("No tickets generated yet.")
        return
    total = build_csv(finished)
    log.info("Wrote %d tickets to %s (%d of %d batches complete)", total, OUT_FILE, len(finished), len(plan))
    if len(finished) < len(plan):
        log.info("Not all batches are done. Run this script again (tomorrow if the daily quota ran out).")


if __name__ == "__main__":
    main()
