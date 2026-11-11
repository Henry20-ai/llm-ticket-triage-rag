"""Central configuration. Everything comes from environment variables or a local .env file.

No secret (API key, database password) is ever written in the code.
"""
import os

from dotenv import load_dotenv

# utf-8-sig also copes with a Byte Order Mark, which some Windows editors add.
load_dotenv(encoding="utf-8-sig")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "")
EMBED_MODEL = os.getenv("EMBED_MODEL", "gemini-embedding-001")
EMBED_DIM = int(os.getenv("EMBED_DIM", "768"))
REQUESTS_PER_MINUTE = int(os.getenv("REQUESTS_PER_MINUTE", "10"))

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "5433")),
    "dbname": os.getenv("DB_NAME", "ticket_triage"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", ""),
}

# Model used only to generate synthetic data (tickets, SOP documents). Falls back to GEMINI_MODEL.
# Using a different model than the triage model keeps their free-tier daily quotas separate.
DATA_GEN_MODEL = os.getenv("DATA_GEN_MODEL", "") or GEMINI_MODEL

# --- Triage settings -------------------------------------------------------------------
# A ticket goes to the human review queue if the model's confidence is below this value...
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.75"))
# ...or if even the best knowledge-base match is weaker than this (the SOPs may not cover it).
MIN_RETRIEVAL_SIMILARITY = float(os.getenv("MIN_RETRIEVAL_SIMILARITY", "0.55"))
# How many knowledge-base chunks to retrieve for each ticket.
TOP_K = int(os.getenv("TOP_K", "3"))

# --- Risk-based human-review rule (v2) -----------------------------------------------------
# Model confidence turned out NOT to predict correctness (see the evaluation report), so tickets
# are also routed to a person by what is at stake: predicted priority and category.
def _csv_set(name: str, default: str) -> set:
    return {item.strip() for item in os.getenv(name, default).split(",") if item.strip()}

REVIEW_PRIORITIES = _csv_set("REVIEW_PRIORITIES", "High,Urgent")
REVIEW_CATEGORIES = _csv_set("REVIEW_CATEGORIES", "Billing & Payments")
