"""Create the database tables from sql/schema.sql.

    python src/init_db.py            create the tables (safe to repeat)
    python src/init_db.py --reset    DROP everything first (deletes all data, embeddings included)
"""
import argparse
from pathlib import Path

import psycopg2

import config

SCHEMA_FILE = Path("sql/schema.sql")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true", help="drop all project tables first")
    args = parser.parse_args()

    connection = psycopg2.connect(**config.DB_CONFIG)
    with connection, connection.cursor() as cursor:
        if args.reset:
            cursor.execute("DROP TABLE IF EXISTS ticket_triage, eval_labels, kb_chunks, tickets CASCADE")
            print("Dropped existing tables.")
        cursor.execute(SCHEMA_FILE.read_text(encoding="utf-8"))
        cursor.execute("SELECT table_name FROM information_schema.tables "
                       "WHERE table_schema = 'public' ORDER BY table_name")
        print("Tables now in the database:", [row[0] for row in cursor.fetchall()])
    connection.close()


if __name__ == "__main__":
    main()
