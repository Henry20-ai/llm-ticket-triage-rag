"""Checks that every piece of the stack works before we build on it.

Run:  python src/check_setup.py

It tests, in order:
  1. the Gemini API key is present
  2. which models your key can actually use (so we never guess model names)
  3. an embedding call returns vectors of the size we configured
  4. a text-generation call works (only if GEMINI_MODEL is set)
  5. Postgres is reachable and the pgvector extension works

Secrets are never printed.
"""
import sys

import psycopg2
from google import genai
from google.genai import types

import config


def report(ok: bool, label: str, detail: str = "") -> bool:
    print(f"[{'PASS' if ok else 'FAIL'}] {label}" + (f"  -  {detail}" if detail else ""))
    return ok


def short(error: Exception) -> str:
    """A one-line error message (trimmed so logs stay readable)."""
    return f"{type(error).__name__}: {str(error)[:220]}"


def main() -> int:
    results = []

    # 1. API key present --------------------------------------------------------
    if not config.GEMINI_API_KEY:
        report(False, "Gemini API key", "GEMINI_API_KEY is empty. Add it to your .env file.")
        return 1
    report(True, "Gemini API key found", "(value hidden)")
    client = genai.Client(api_key=config.GEMINI_API_KEY)

    # 2. Models available to this key -------------------------------------------
    try:
        models = list(client.models.list())
        names_by_action = {"generateContent": [], "embedContent": []}
        for model in models:
            short_name = model.name.replace("models/", "")
            for action in (getattr(model, "supported_actions", None) or []):
                if action in names_by_action:
                    names_by_action[action].append(short_name)
        flash = sorted(n for n in names_by_action["generateContent"] if "flash" in n)
        report(True, f"Model list ({len(models)} models visible to your key)")
        print("       Text-generation models containing 'flash':")
        for name in flash[:20]:
            print(f"         - {name}")
        print("       Embedding models:")
        for name in sorted(names_by_action["embedContent"]):
            print(f"         - {name}")
        results.append(True)
    except Exception as error:  # noqa: BLE001 - we want to show any failure clearly
        results.append(report(False, "Model list", short(error)))

    # 3. Embeddings ---------------------------------------------------------------
    try:
        response = client.models.embed_content(
            model=config.EMBED_MODEL,
            contents=["Customer cannot reset their password"],
            config=types.EmbedContentConfig(
                task_type="RETRIEVAL_DOCUMENT",
                output_dimensionality=config.EMBED_DIM,
            ),
        )
        size = len(response.embeddings[0].values)
        results.append(report(size == config.EMBED_DIM, f"Embedding ({config.EMBED_MODEL})",
                              f"vector size {size}, expected {config.EMBED_DIM}"))
    except Exception as error:  # noqa: BLE001
        results.append(report(False, f"Embedding ({config.EMBED_MODEL})", short(error)))

    # 4. Text generation ----------------------------------------------------------
    if not config.GEMINI_MODEL:
        print("[SKIP] Text generation  -  GEMINI_MODEL is empty. Pick a model from the list "
              "above, put it in .env, and run this again.")
    else:
        try:
            response = client.models.generate_content(
                model=config.GEMINI_MODEL, contents="Reply with the single word: ready")
            results.append(report(True, f"Generation ({config.GEMINI_MODEL})",
                                  f"model replied: {response.text.strip()[:40]!r}"))
        except Exception as error:  # noqa: BLE001
            results.append(report(False, f"Generation ({config.GEMINI_MODEL})", short(error)))

    # 5. Postgres + pgvector --------------------------------------------------------
    try:
        connection = psycopg2.connect(**config.DB_CONFIG, connect_timeout=5)
        cursor = connection.cursor()
        cursor.execute("SELECT extversion FROM pg_extension WHERE extname = 'vector'")
        row = cursor.fetchone()
        if row is None:
            results.append(report(False, "pgvector extension",
                                  "not enabled. Run: CREATE EXTENSION IF NOT EXISTS vector;"))
        else:
            cursor.execute("SELECT '[1,2,3]'::vector <=> '[1,2,4]'::vector")
            distance = cursor.fetchone()[0]
            results.append(report(True, "Postgres + pgvector",
                                  f"extension version {row[0]}, test cosine distance {distance:.6f}"))
        connection.close()
    except Exception as error:  # noqa: BLE001
        results.append(report(False, "Postgres connection", short(error)))

    print()
    print("ALL CHECKS PASSED" if all(results) else "Some checks failed - fix them before continuing.")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
