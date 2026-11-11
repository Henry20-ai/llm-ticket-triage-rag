"""Step 3a: Gemini writes the fake SOP knowledge base (25 short documents).

Output: data/sops/NN_title.md. Documents that already exist are skipped, so the script
is safe to re-run. All documents receive the same POLICY_FACTS so they never contradict
each other.

Run:  python src/generate_kb.py
"""
import logging
import re
from pathlib import Path

from google.genai import errors

import config
from kb_topics import POLICY_FACTS, SOP_TOPICS
from llm_utils import generate_text
from taxonomy import COMPANY_CONTEXT, PRIORITY_GUIDE

log = logging.getLogger("rag")
SOP_DIR = Path("data/sops")


def slugify(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_")


def build_prompt(title: str, category: str, scope: str) -> str:
    priority_text = "\n".join(f"- {name}: {text}" for name, text in PRIORITY_GUIDE.items())
    return f"""Write the internal SOP (standard operating procedure) titled "{title}" for Brightcart's customer support team.
Main ticket category it supports: {category}
Scope: {scope}

Company policy facts. Use them exactly and never contradict them:
{POLICY_FACTS}

Priority definitions used by the support team:
{priority_text}

Write it in Markdown with exactly these sections, in this order:
# {title}
## Purpose
## When this applies
## Steps for the agent   (numbered, concrete)
## What to tell the customer   (sample wording, 2-3 sentences)
## Escalation and priority   (say clearly when this situation is Low, Medium, High or Urgent, and when to escalate)
## Common mistakes

Length: 350 to 500 words. Be specific and practical, with concrete numbers consistent with the policy facts. No placeholders such as [insert ...]."""


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s", datefmt="%H:%M:%S")
    if not config.DATA_GEN_MODEL:
        raise RuntimeError("Set GEMINI_MODEL (or DATA_GEN_MODEL) in your .env file first.")
    SOP_DIR.mkdir(parents=True, exist_ok=True)

    written = 0
    for number, (title, category, scope) in enumerate(SOP_TOPICS, start=1):
        path = SOP_DIR / f"{number:02d}_{slugify(title)}.md"
        if path.exists() and path.stat().st_size > 500:
            continue
        try:
            text = generate_text(build_prompt(title, category, scope), model=config.DATA_GEN_MODEL,
                                 system=f"You write clear internal documentation. {COMPANY_CONTEXT}",
                                 temperature=0.6)
        except errors.APIError as error:
            log.error("Gemini stopped us (%s). Progress is saved: run the script again later.", error)
            break
        path.write_text(text, encoding="utf-8")
        written += 1
        log.info("Wrote %s (%d words)", path.name, len(text.split()))

    total = len(list(SOP_DIR.glob("*.md")))
    log.info("Done. %d new documents this run, %d of %d in %s", written, total, len(SOP_TOPICS), SOP_DIR)


if __name__ == "__main__":
    main()
