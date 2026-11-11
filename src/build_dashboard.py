"""Build the static HTML dashboard from the database.

    python src/build_dashboard.py

Reads the triage results, the evaluation labels and the review queue from Postgres and writes ONE
self-contained page, docs/index.html (the data is embedded in the file; only the Chart.js library is
loaded from a CDN). Open it by double-clicking, or host it for free with GitHub Pages
(repository Settings -> Pages -> branch main, folder /docs).

Optional: set DASHBOARD_REPO_URL in .env to show a link to the source code in the footer.
"""
import json
import os
from datetime import datetime
from pathlib import Path

import pandas as pd
import psycopg2

import config
import evaluate as ev
from taxonomy import CATEGORIES, PRIORITIES

TEMPLATE = Path(__file__).with_name("dashboard_template.html")
OUT_FILE = Path("docs/index.html")


# --------------------------------------------------------------------------- helpers
def clean(value):
    """Make a value safe for JSON: NaN/NaT -> None, numpy numbers -> plain Python numbers."""
    if value is None or (not isinstance(value, (str, bool)) and pd.isna(value)):
        return None
    if hasattr(value, "item"):
        return value.item()
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.isoformat(sep=" ")
    return value


def stat(successes: int, n: int) -> dict:
    low, high = ev.wilson_interval(int(successes), n)
    return {"k": int(successes), "n": n, "pct": round(100 * successes / n, 1), "lo": round(100 * low), "hi": round(100 * high)}


# --------------------------------------------------------------------------- data loading
def load_tickets(connection) -> tuple:
    with connection.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM tickets")
        total = cursor.fetchone()[0]
        cursor.execute("""
            SELECT t.ticket_id, t.ticket_text, t.created_at, t.resolved_at,
                   tr.category, tr.priority, tr.confidence, tr.needs_review, tr.review_reason,
                   tr.suggested_reply, tr.reasoning
            FROM tickets t JOIN ticket_triage tr USING (ticket_id) ORDER BY t.ticket_id""")
        columns = [column[0] for column in cursor.description]
        rows = cursor.fetchall()
    return total, pd.DataFrame(rows, columns=columns)


# --------------------------------------------------------------------------- ticket statistics
def ticket_payload(df: pd.DataFrame, total_tickets: int) -> dict:
    df = df.copy()
    df["confidence"] = df["confidence"].astype(float)
    df["created_at"] = pd.to_datetime(df["created_at"])
    df["resolved_at"] = pd.to_datetime(df["resolved_at"])
    df["hours"] = (df["resolved_at"] - df["created_at"]).dt.total_seconds() / 3600
    n = len(df)
    review = int(df["needs_review"].sum())

    by_category = []
    for category in CATEGORIES:
        group = df[df["category"] == category]
        by_category.append({"category": category, "count": len(group), "review": int(group["needs_review"].sum())})

    by_priority = [{"priority": p, "count": int((df["priority"] == p).sum())} for p in PRIORITIES]
    resolution = [{"priority": p, "hours": clean(round(df[(df["priority"] == p)]["hours"].mean(), 1))} for p in PRIORITIES]
    resolution = [r for r in resolution if r["hours"] is not None]

    weeks = df["created_at"].dt.to_period("W-SUN").dt.start_time.dt.strftime("%Y-%m-%d")
    weekly = [{"week": week, "count": int(count)} for week, count in weeks.value_counts().sort_index().items()]

    tickets = [{
        "id": int(r.ticket_id), "text": r.ticket_text, "category": r.category, "priority": r.priority,
        "confidence": float(r.confidence), "needs_review": bool(r.needs_review),
        "review_reason": clean(r.review_reason) or "", "reply": r.suggested_reply, "reasoning": clean(r.reasoning) or "",
    } for r in df.itertuples()]

    return {
        "kpis": {
            "total_tickets": total_tickets, "triaged": n, "review_count": review,
            "review_pct": round(100 * review / n) if n else 0, "auto_pct": round(100 * (n - review) / n) if n else 0,
            "avg_resolution_hours": clean(round(df["hours"].mean(), 1)),
            "open_tickets": int(df["resolved_at"].isna().sum()),
        },
        "by_category": by_category, "by_priority": by_priority, "resolution_by_priority": resolution,
        "weekly": weekly, "tickets": tickets,
    }


# --------------------------------------------------------------------------- evaluation statistics
def prepare_eval(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["confidence"] = df["confidence"].astype(float)
    df["top_similarity"] = df["top_similarity"].astype(float)
    df["cat_ok"] = df["human_category"] == df["category"]
    df["pri_ok"] = df["human_priority"] == df["priority"]
    df["both_ok"] = df["cat_ok"] & df["pri_ok"]
    df["pri_diff"] = df["priority"].map(ev.RANK) - df["human_priority"].map(ev.RANK)
    df["sop_category"] = df["sop_doc"].map(ev.DOC_CATEGORY)
    return df


def eval_metrics(df: pd.DataFrame, second: pd.DataFrame | None = None) -> dict:
    df = prepare_eval(df)
    n = len(df)
    urgent = df["human_priority"] == "Urgent"
    n_wrong = int((~df["both_ok"]).sum())

    rules = []
    for name, flagged in ev.review_rule_masks(df).items():
        auto = df[~flagged]
        rules.append({
            "rule": name, "flagged": int(flagged.sum()), "flagged_pct": round(100 * flagged.mean()),
            "caught": int((flagged & ~df["both_ok"]).sum()), "wrong": n_wrong,
            "urgent_missed": int((urgent & (df["priority"] != "Urgent") & ~flagged).sum()), "urgent_total": int(urgent.sum()),
        })

    metrics = {
        "n": n,
        "category": stat(df["cat_ok"].sum(), n), "priority": stat(df["pri_ok"].sum(), n),
        "priority_within_one": stat((df["pri_diff"].abs() <= 1).sum(), n), "both": stat(df["both_ok"].sum(), n),
        "stated_confidence": round(df["confidence"].mean(), 2), "actual_both": round(df["both_ok"].mean(), 2),
        "urgent": {"total": int(urgent.sum()), "rated_lower": int((urgent & (df["priority"] != "Urgent")).sum())},
        "rules": rules,
    }
    if second is not None and len(second):
        both = df.merge(second, on="ticket_id")
        m = len(both)
        if m >= 5:
            metrics["agreement"] = {
                "n": m,
                "category": stat((both["human_category"] == both["second_category"]).sum(), m),
                "priority": stat((both["human_priority"] == both["second_priority"]).sum(), m),
                "category_kappa": round(ev.cohen_kappa(both["human_category"].tolist(), both["second_category"].tolist()), 2),
                "priority_kappa": round(ev.cohen_kappa(both["human_priority"].tolist(), both["second_priority"].tolist()), 2),
                "ai_category": stat((both["category"] == both["second_category"]).sum(), m),
                "ai_priority": stat((both["priority"] == both["second_priority"]).sum(), m),
            }
    return metrics


# --------------------------------------------------------------------------- page
def render_html(payload: dict) -> str:
    """Put the data into the page template. '</' is escaped so ticket text can never close the script tag."""
    data = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    return TEMPLATE.read_text(encoding="utf-8").replace("__DATA__", data)


def main() -> None:
    connection = psycopg2.connect(**config.DB_CONFIG)
    total, tickets = load_tickets(connection)
    connection.close()
    if tickets.empty:
        raise SystemExit("No triage results yet. Run triage_tickets.py first.")

    payload = ticket_payload(tickets, total)
    payload["generated_at"] = datetime.now().strftime("%d %b %Y")
    payload["repo_url"] = os.getenv("DASHBOARD_REPO_URL", "")
    payload["evaluation"] = {}
    for eval_set in ("test", "dev"):
        results = ev.load_results(eval_set)
        if not results.empty:
            second = ev.load_second_labels("friend") if eval_set == "test" else None
            payload["evaluation"][eval_set] = eval_metrics(results, second)

    OUT_FILE.parent.mkdir(exist_ok=True)
    OUT_FILE.write_text(render_html(payload), encoding="utf-8")
    kpis = payload["kpis"]
    print(f"Wrote {OUT_FILE} ({OUT_FILE.stat().st_size // 1024} KB): {kpis['triaged']} of {kpis['total_tickets']} tickets triaged, "
          f"{kpis['review_pct']}% sent to a person, evaluation sets: {sorted(payload['evaluation'])}")
    if kpis["triaged"] < kpis["total_tickets"]:
        print(f"Note: only {kpis['triaged']} of {kpis['total_tickets']} tickets are triaged. Run `python src/triage_tickets.py` to finish the rest, then rebuild.")


if __name__ == "__main__":
    main()
