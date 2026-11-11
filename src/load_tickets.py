"""Step 2: load data/tickets.csv into the Postgres `tickets` table.

    python src/load_tickets.py            load (refuses if the table already has rows)
    python src/load_tickets.py --reset    empty the project tables first, then load
"""
import argparse
import csv
from pathlib import Path

import psycopg2
from psycopg2.extras import execute_values

import config

CSV_FILE = Path("data/tickets.csv")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true", help="empty tickets (and triage results) first")
    args = parser.parse_args()

    with CSV_FILE.open(newline="", encoding="utf-8") as file:
        rows = [(r["ticket_text"], r["generated_category"], r["generated_priority"],
                 r["created_at"], r["resolved_at"] or None) for r in csv.DictReader(file)]

    connection = psycopg2.connect(**config.DB_CONFIG)
    with connection, connection.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM tickets")
        existing = cursor.fetchone()[0]
        if existing and not args.reset:
            print(f"The tickets table already has {existing} rows. Use --reset to replace them.")
            return
        if args.reset:
            cursor.execute("TRUNCATE ticket_triage, eval_labels, tickets RESTART IDENTITY CASCADE")
        execute_values(
            cursor,
            "INSERT INTO tickets (ticket_text, generated_category, generated_priority, created_at, resolved_at) VALUES %s",
            rows)
        cursor.execute("SELECT COUNT(*) FROM tickets")
        print(f"Loaded {len(rows)} tickets. Rows in table: {cursor.fetchone()[0]}")
    connection.close()


if __name__ == "__main__":
    main()
