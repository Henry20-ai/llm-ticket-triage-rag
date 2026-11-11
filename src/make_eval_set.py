"""Pick tickets for you (and optionally a friend) to label by hand, and write the labelling guide.

    python src/make_eval_set.py          the 50-ticket DEV set (refuses to overwrite a file you may have labelled)
    python src/make_eval_set.py --test   a FRESH 40-ticket TEST set that excludes every dev ticket
    add --force to overwrite an existing file

Writes data/eval_to_label.csv or data/test_to_label.csv (columns: ticket_id, ticket_text,
human_category, human_priority - the last two blank) and always refreshes data/labeling_guide.md
with the current (v2) category rules and priority definitions.

The generator's own labels are deliberately NOT included, so they cannot influence the labeller.
The tickets are shuffled and sampled evenly across categories.
"""
import argparse
import csv
import random
from collections import defaultdict
from pathlib import Path

import psycopg2

import config
from taxonomy import CATEGORIES, CATEGORY_RULES, PRIORITIES, PRIORITY_GUIDE, TAXONOMY_VERSION

DEV_FILE = Path("data/eval_to_label.csv")
TEST_FILE = Path("data/test_to_label.csv")
GUIDE_FILE = Path("data/labeling_guide.md")
DEV_PER_CATEGORY = {
    "Billing & Payments": 9, "Delivery & Shipping": 10, "Returns & Refunds": 7,
    "Account & Access": 6, "Product Issue": 6, "App & Website Issues": 6, "General Inquiry": 6,
}
TEST_PER_CATEGORY = {      # 40 tickets
    "Billing & Payments": 7, "Delivery & Shipping": 8, "Returns & Refunds": 5,
    "Account & Access": 5, "Product Issue": 5, "App & Website Issues": 5, "General Inquiry": 5,
}


def pick_sample(rows: list, per_category: dict, rng: random.Random, exclude_ids=frozenset()) -> list:
    """rows = (ticket_id, ticket_text, generated_category). Shuffled stratified sample, skipping excluded ids."""
    by_category = defaultdict(list)
    for row in rows:
        if row[0] not in exclude_ids:
            by_category[row[2]].append(row)
    sample = []
    for category, count in per_category.items():
        sample.extend(rng.sample(by_category[category], count))
    rng.shuffle(sample)
    return sample


def guide_text() -> str:
    lines = [f"# Labelling guide ({TAXONOMY_VERSION})", "",
             "For every ticket choose ONE category and ONE priority. Judge the customer's situation, "
             "not their tone or wording. Do not look at any AI output until you have finished all tickets, "
             "and do not discuss your labels with anyone who is labelling the same tickets.", "",
             "## Categories"]
    lines += [f"- **{name}**: {text}" for name, text in CATEGORIES.items()]
    lines += ["", "## Category rules (use them to break ties)"]
    lines += [f"{number}. {text}" for number, text in enumerate(CATEGORY_RULES, start=1)]
    lines += ["", "## Priorities"]
    lines += [f"- **{name}**: {PRIORITY_GUIDE[name]}" for name in reversed(PRIORITIES)]
    lines += ["", "Type the category and priority EXACTLY as written above (copy and paste, or use the dropdowns)."]
    return "\n".join(lines)


def read_ids(path: Path) -> set:
    with path.open(newline="", encoding="utf-8-sig") as file:
        return {int(row["ticket_id"]) for row in csv.DictReader(file)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", action="store_true", help="make the fresh test set instead of the dev set")
    parser.add_argument("--force", action="store_true", help="overwrite an existing file")
    args = parser.parse_args()
    target = TEST_FILE if args.test else DEV_FILE
    if target.exists() and not args.force:
        print(f"{target} already exists. It may contain labels, so it was not overwritten. Use --force to replace it.")
        return

    exclude = set()
    if args.test:
        if not DEV_FILE.exists():
            raise SystemExit(f"{DEV_FILE} not found: the test set must exclude the dev tickets.")
        exclude = read_ids(DEV_FILE)

    connection = psycopg2.connect(**config.DB_CONFIG)
    with connection.cursor() as cursor:
        cursor.execute("SELECT ticket_id, ticket_text, generated_category FROM tickets ORDER BY ticket_id")
        rows = cursor.fetchall()
    connection.close()

    per_category = TEST_PER_CATEGORY if args.test else DEV_PER_CATEGORY
    sample = pick_sample(rows, per_category, random.Random(11 if args.test else 7), exclude)
    with target.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["ticket_id", "ticket_text", "human_category", "human_priority"])
        for ticket_id, text, _ in sample:
            writer.writerow([ticket_id, text, "", ""])
    GUIDE_FILE.write_text(guide_text(), encoding="utf-8")
    print(f"Wrote {len(sample)} tickets to {target} and the {TAXONOMY_VERSION} guide to {GUIDE_FILE}")


if __name__ == "__main__":
    main()
