"""Validate hand labels and load them into the database.

    python src/load_eval_labels.py                       your dev labels   (data/eval_to_label.csv)
    python src/load_eval_labels.py --set test            your test labels  (data/test_to_label.csv)
    python src/load_eval_labels.py --annotator friend --file data/test_friend.csv
                                                         a second person's labels (stored separately)

Every row must be filled in and spelled exactly like the categories / priorities in
data/labeling_guide.md (capital letters do not matter). Nothing is loaded until all rows are valid.
"""
import argparse
import csv
from pathlib import Path

import psycopg2
from psycopg2.extras import execute_values

import config
from taxonomy import CATEGORIES, PRIORITIES

DEFAULT_FILES = {"dev": Path("data/eval_to_label.csv"), "test": Path("data/test_to_label.csv")}


def normalise(value: str, allowed) -> str | None:
    """Match text to an allowed value ignoring capital letters and stray spaces."""
    lookup = {name.lower(): name for name in allowed}
    return lookup.get(" ".join((value or "").split()).lower())


def validate(rows: list) -> tuple:
    """Return (clean_rows, problems). clean_rows = (ticket_id, category, priority)."""
    clean, problems = [], []
    for line_number, row in enumerate(rows, start=2):       # line 1 is the header
        category = normalise(row.get("human_category"), CATEGORIES)
        priority = normalise(row.get("human_priority"), PRIORITIES)
        if category is None:
            problems.append(f"line {line_number}: human_category {row.get('human_category')!r} is empty or not one of {list(CATEGORIES)}")
        if priority is None:
            problems.append(f"line {line_number}: human_priority {row.get('human_priority')!r} is empty or not one of {PRIORITIES}")
        if category and priority:
            clean.append((int(row["ticket_id"]), category, priority))
    return clean, problems


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--set", choices=["dev", "test"], default="dev", help="which evaluation set these labels belong to")
    parser.add_argument("--annotator", default="henry", help="'henry' = main labels; any other name = second labeller")
    parser.add_argument("--file", help="CSV to load (default depends on --set)")
    args = parser.parse_args()
    path = Path(args.file) if args.file else DEFAULT_FILES[args.set]

    # utf-8-sig also reads files re-saved by Excel (which can add a hidden marker at the start).
    with path.open(newline="", encoding="utf-8-sig") as file:
        rows = list(csv.DictReader(file))
    clean, problems = validate(rows)
    if problems:
        print(f"{len(problems)} problem(s) found. Fix them in {path} and run again:")
        for problem in problems[:25]:
            print("  -", problem)
        return

    connection = psycopg2.connect(**config.DB_CONFIG)
    with connection, connection.cursor() as cursor:
        if args.annotator == "henry":
            execute_values(
                cursor,
                """INSERT INTO eval_labels (ticket_id, human_category, human_priority, eval_set) VALUES %s
                   ON CONFLICT (ticket_id) DO UPDATE SET human_category = EXCLUDED.human_category,
                       human_priority = EXCLUDED.human_priority, eval_set = EXCLUDED.eval_set""",
                [(ticket_id, category, priority, args.set) for ticket_id, category, priority in clean])
            cursor.execute("SELECT eval_set, COUNT(*) FROM eval_labels GROUP BY eval_set ORDER BY eval_set")
            print(f"Loaded {len(clean)} labels from {path}. eval_labels now holds:", dict(cursor.fetchall()))
        else:
            execute_values(
                cursor,
                """INSERT INTO second_labels (ticket_id, annotator, human_category, human_priority) VALUES %s
                   ON CONFLICT (ticket_id, annotator) DO UPDATE SET human_category = EXCLUDED.human_category,
                       human_priority = EXCLUDED.human_priority""",
                [(ticket_id, args.annotator, category, priority) for ticket_id, category, priority in clean])
            print(f"Loaded {len(clean)} labels from annotator '{args.annotator}'.")
    connection.close()


if __name__ == "__main__":
    main()
