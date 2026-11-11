"""Compare the AI triage with hand labels, honestly.

    python src/evaluate.py                 the dev set
    python src/evaluate.py --set test      the fresh test set (the numbers to quote)

Reads eval_labels (your labels) joined with ticket_triage (the AI results) and reports:
  * category accuracy, priority accuracy (exact and within one level) and both-correct, each with a
    95% confidence interval and compared with a "always guess the most common label" baseline
  * how real Urgent tickets were handled (under-rating them is the dangerous mistake)
  * which categories get confused, and whether priority is over- or under-estimated
  * whether the model's confidence score can be trusted
  * several human-review rules compared (workload vs mistakes caught)
  * how often two humans agree (if a second labeller's labels are loaded) = a realistic ceiling for the AI
  * every mistake, most confident ones first

Outputs: output/evaluation_report_<set>.md and output/eval_errors_<set>.csv
"""
import argparse
import math
from pathlib import Path

import pandas as pd
import psycopg2

import config
from kb_topics import SOP_TOPICS
from taxonomy import CATEGORIES, PRIORITIES

OUT_DIR = Path("output")
DOC_CATEGORY = {title: category for title, category, _ in SOP_TOPICS}   # SOP title -> category
RANK = {name: number for number, name in enumerate(PRIORITIES)}         # Low=0 ... Urgent=3
CONFIDENCE_BINS = [0, 0.8, 0.9, 0.95, 1.01]
CONFIDENCE_LABELS = ["below 0.80", "0.80 - 0.89", "0.90 - 0.94", "0.95 - 1.00"]


# --------------------------------------------------------------------------- statistics
def wilson_interval(successes: int, n: int, z: float = 1.96) -> tuple:
    """95% confidence interval for a proportion (honest about small samples)."""
    if n == 0:
        return 0.0, 0.0
    p = successes / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    margin = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return centre - margin, centre + margin


def fmt(successes: int, n: int) -> str:
    low, high = wilson_interval(successes, n)
    return f"{100 * successes / n:.1f}% ({successes}/{n}, 95% CI {100 * low:.0f}-{100 * high:.0f}%)"


def cohen_kappa(a: list, b: list) -> float:
    """Agreement between two labellers after removing agreement expected by chance (1 = perfect, 0 = chance)."""
    n = len(a)
    labels = set(a) | set(b)
    observed = sum(x == y for x, y in zip(a, b)) / n
    expected = sum((a.count(label) / n) * (b.count(label) / n) for label in labels)
    return 1.0 if expected == 1 else (observed - expected) / (1 - expected)


# --------------------------------------------------------------------------- data loading
def load_results(eval_set: str) -> pd.DataFrame:
    connection = psycopg2.connect(**config.DB_CONFIG)
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT e.ticket_id, t.ticket_text, e.human_category, e.human_priority,
                   tr.category, tr.priority, tr.confidence, tr.top_similarity, tr.needs_review, tr.reasoning,
                   k.doc_title AS sop_doc, tr.prompt_version, tr.review_reason
            FROM eval_labels e
            JOIN tickets t USING (ticket_id)
            JOIN ticket_triage tr USING (ticket_id)
            LEFT JOIN kb_chunks k ON k.chunk_id = tr.source_chunk_ids[1]
            WHERE e.eval_set = %s
            ORDER BY e.ticket_id""", (eval_set,))
        columns = [column[0] for column in cursor.description]
        rows = cursor.fetchall()
    connection.close()
    return pd.DataFrame(rows, columns=columns)


def load_second_labels(annotator: str) -> pd.DataFrame:
    connection = psycopg2.connect(**config.DB_CONFIG)
    with connection.cursor() as cursor:
        cursor.execute("SELECT ticket_id, human_category AS second_category, human_priority AS second_priority "
                       "FROM second_labels WHERE annotator = %s", (annotator,))
        columns = [column[0] for column in cursor.description]
        rows = cursor.fetchall()
    connection.close()
    return pd.DataFrame(rows, columns=columns)


# --------------------------------------------------------------------------- review rules
def review_rule_masks(df: pd.DataFrame) -> dict:
    """Candidate review rules as True/False per ticket (True = goes to a person)."""
    priority_rule = df["priority"].isin(config.REVIEW_PRIORITIES)
    category_rule = df["category"].isin(config.REVIEW_CATEGORIES)
    masks = {
        "v1: low confidence / weak match": (df["confidence"] < 0.75) | (df["top_similarity"] < 0.55),
        "predicted " + "/".join(sorted(config.REVIEW_PRIORITIES, key=PRIORITIES.index)): priority_rule,
        "category " + "/".join(sorted(config.REVIEW_CATEGORIES)): category_rule,
        "CURRENT RULE: priority or category": priority_rule | category_rule,
    }
    if "sop_category" in df.columns and df["sop_category"].notna().any():
        masks["current rule + SOP category differs"] = priority_rule | category_rule | (df["sop_category"] != df["category"])
    return masks


def review_rule_section(df: pd.DataFrame) -> list:
    n_wrong = int((~df["both_ok"]).sum())
    urgent = df["human_priority"] == "Urgent"
    out = ["## Human-review rules compared", "",
           "Flagged = sent to a person. 'Mistakes caught' = share of wrong answers that were flagged. "
           "'Urgent missed' = real Urgent tickets the AI rated lower AND did not flag (the dangerous ones). "
           "The more tickets a rule flags, the less work the AI saves, so this is a trade-off, not a single best answer.", "", "```",
           f"{'rule':<40}{'flagged':>12}{'mistakes caught':>17}{'Urgent missed':>15}{'unreviewed accuracy':>21}"]
    for name, flagged in review_rule_masks(df).items():
        auto = df[~flagged]
        silent = int((urgent & (df["priority"] != "Urgent") & ~flagged).sum())
        caught = f"{int((flagged & ~df['both_ok']).sum())}/{n_wrong}"
        accuracy = f"{100 * auto['both_ok'].mean():.0f}% ({len(auto)})" if len(auto) else "-"
        out.append(f"{name:<40}{f'{int(flagged.sum())} ({100 * flagged.mean():.0f}%)':>12}{caught:>17}"
                   f"{f'{silent}/{int(urgent.sum())}':>15}{accuracy:>21}")
    out += ["```", "",
            "Rules were chosen after reading mistakes on the dev set, so judge them on the test set, not here.", ""]
    return out


# --------------------------------------------------------------------------- the report
def compute_report(df: pd.DataFrame, set_name: str = "dev", second: pd.DataFrame | None = None) -> tuple:
    """Return (markdown_lines, errors_dataframe). Separated from the database code so it can be tested."""
    df = df.copy()
    df["confidence"] = df["confidence"].astype(float)
    df["top_similarity"] = df["top_similarity"].astype(float)
    df["cat_ok"] = df["human_category"] == df["category"]
    df["pri_ok"] = df["human_priority"] == df["priority"]
    df["both_ok"] = df["cat_ok"] & df["pri_ok"]
    df["pri_diff"] = df["priority"].map(RANK) - df["human_priority"].map(RANK)    # + = AI too high
    if "sop_doc" in df.columns:
        df["sop_category"] = df["sop_doc"].map(DOC_CATEGORY)
    n = len(df)
    versions = ", ".join(sorted(df["prompt_version"].dropna().unique())) if "prompt_version" in df.columns else "unknown"

    out = [f"# Evaluation report ({set_name} set)", "",
           f"Tickets evaluated: **{n}** (labelled by hand, never seen by the model). Prompt version(s) in these results: {versions}. "
           "With this few tickets every percentage has a wide margin of error (see the intervals).", "",
           "## Overall accuracy", ""]
    cat_base = df["human_category"].value_counts().iloc[0]
    pri_base = df["human_priority"].value_counts().iloc[0]
    out += [
        f"- Category accuracy: **{fmt(int(df.cat_ok.sum()), n)}**  (baseline, always guess the most common category: {100 * cat_base / n:.0f}%)",
        f"- Priority accuracy (exact): **{fmt(int(df.pri_ok.sum()), n)}**  (baseline, always guess the most common priority: {100 * pri_base / n:.0f}%)",
        f"- Priority within one level: **{fmt(int((df.pri_diff.abs() <= 1).sum()), n)}**",
        f"- Category AND priority both correct: **{fmt(int(df.both_ok.sum()), n)}**",
        f"- Priority bias: AI too high on {int((df.pri_diff > 0).sum())} tickets, too low on {int((df.pri_diff < 0).sum())} "
        f"(average difference {df.pri_diff.mean():+.2f} levels; positive = AI rates tickets more serious than you did)", ""]

    urgent = df["human_priority"] == "Urgent"
    out += ["## Real Urgent tickets", "",
            f"- You labelled {int(urgent.sum())} tickets Urgent. The AI also said Urgent on {int((urgent & (df.priority == 'Urgent')).sum())}; "
            f"it rated {int((urgent & (df.priority != 'Urgent')).sum())} lower (the dangerous direction).",
            f"- The AI said Urgent on {int(((~urgent) & (df.priority == 'Urgent')).sum())} tickets you did not label Urgent (extra work, but safe).", ""]

    out += ["## Category accuracy by true category (your labels)", "", "```"]
    per_cat = df.groupby("human_category")["cat_ok"].agg(["sum", "count"]).reindex(list(CATEGORIES)).dropna()
    for name, row in per_cat.iterrows():
        out.append(f"{name:<22} {int(row['sum'])}/{int(row['count'])}  ({100 * row['sum'] / row['count']:.0f}%)")
    out += ["```", "", "## Category mistakes (you said -> AI said)", "", "```"]
    wrong = df[~df.cat_ok].groupby(["human_category", "category"]).size().sort_values(ascending=False)
    out += [f"{count}x  {human}  ->  {ai}" for (human, ai), count in wrong.items()] or ["none"]
    out += ["```", "", "## Priority confusion matrix (rows = your label, columns = AI)", "", "```"]
    matrix = pd.crosstab(df["human_priority"], df["priority"]).reindex(index=PRIORITIES, columns=PRIORITIES, fill_value=0)
    out += [matrix.to_string(), "```", ""]

    out += ["## Can the confidence score be trusted?", "",
            "Accuracy here means category AND priority both correct. If confidence were reliable, accuracy would rise with it.", "", "```"]
    df["band"] = pd.cut(df["confidence"], bins=CONFIDENCE_BINS, labels=CONFIDENCE_LABELS, right=False)
    for band, group in df.groupby("band", observed=True):
        out.append(f"confidence {band:<12} tickets: {len(group):>2}   both correct: {100 * group.both_ok.mean():>3.0f}%")
    out += ["```", "",
            f"Average stated confidence: {df.confidence.mean():.2f}. Actual both-correct rate: {df.both_ok.mean():.2f}. "
            f"Gap (overconfidence): {df.confidence.mean() - df.both_ok.mean():+.2f}", ""]

    if "sop_category" in df.columns and df["sop_category"].notna().any():
        agree = df["sop_category"] == df["category"]
        out += ["## Does the best-matching SOP agree with the AI?", "", "```"]
        for label, mask in (("SOP category = AI category", agree), ("SOP category differs", ~agree)):
            group = df[mask]
            if len(group):
                out.append(f"{label:<28} tickets: {len(group):>2}   category correct: {100 * group.cat_ok.mean():>3.0f}%"
                           f"   both correct: {100 * group.both_ok.mean():>3.0f}%")
        out += ["```", ""]
    df["sim_band"] = pd.cut(df["top_similarity"], bins=[0, 0.60, 0.65, 0.70, 1.01],
                            labels=["below 0.60", "0.60 - 0.64", "0.65 - 0.69", "0.70 and above"], right=False)
    out += ["## Accuracy by retrieval similarity", "", "```"]
    for band, group in df.groupby("sim_band", observed=True):
        out.append(f"similarity {band:<15} tickets: {len(group):>2}   category correct: {100 * group.cat_ok.mean():>3.0f}%"
                   f"   both correct: {100 * group.both_ok.mean():>3.0f}%")
    out += ["```", "", "## Category counts: your labels vs the AI", "", "```", f"{'category':<22}{'you':>5}{'AI':>5}"]
    human_counts, ai_counts = df["human_category"].value_counts(), df["category"].value_counts()
    for name in CATEGORIES:
        out.append(f"{name:<22}{human_counts.get(name, 0):>5}{ai_counts.get(name, 0):>5}")
    out += ["```", ""]

    out += review_rule_section(df)

    if second is not None and len(second):
        both = df.merge(second, on="ticket_id")
        m = len(both)
        if m >= 5:
            cat_agree = int((both.human_category == both.second_category).sum())
            pri_agree = int((both.human_priority == both.second_priority).sum())
            pri_near = int(((both.human_priority.map(RANK) - both.second_priority.map(RANK)).abs() <= 1).sum())
            ai_cat = int((both.category == both.second_category).sum())
            ai_pri = int((both.priority == both.second_priority).sum())
            out += ["## How often do two humans agree?", "",
                    f"Tickets labelled by both of you: **{m}**. Where two people disagree there is no single 'correct' answer, "
                    "so the human agreement rate is a realistic ceiling for the AI.", "",
                    f"- Category agreement (you vs second labeller): **{fmt(cat_agree, m)}**, Cohen's kappa {cohen_kappa(both.human_category.tolist(), both.second_category.tolist()):.2f}",
                    f"- Priority agreement (exact): **{fmt(pri_agree, m)}**, within one level {fmt(pri_near, m)}, Cohen's kappa {cohen_kappa(both.human_priority.tolist(), both.second_priority.tolist()):.2f}",
                    f"- AI vs the second labeller: category {fmt(ai_cat, m)}, priority {fmt(ai_pri, m)}", ""]

    errors = df[~df.both_ok].sort_values("confidence", ascending=False).copy()
    errors["ticket_text"] = errors["ticket_text"].str.slice(0, 220)
    keep = ["ticket_id", "ticket_text", "human_category", "category", "human_priority", "priority",
            "confidence", "top_similarity", "needs_review", "reasoning"]
    errors = errors[keep]
    out += [f"## Mistakes: {len(errors)} tickets", "",
            f"Saved to output/eval_errors_{set_name}.csv, most confident mistakes first (the dangerous ones)."]
    return out, errors


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--set", choices=["dev", "test"], default="dev", help="which evaluation set to report on")
    parser.add_argument("--second-annotator", default="friend", help="name used when loading the second labeller's labels")
    args = parser.parse_args()

    df = load_results(args.set)
    if df.empty:
        print(f"No tickets in the '{args.set}' set with BOTH a hand label and a triage result. "
              "Run load_eval_labels.py and triage_tickets.py first.")
        return
    second = load_second_labels(args.second_annotator)
    lines, errors = compute_report(df, args.set, second)
    OUT_DIR.mkdir(exist_ok=True)
    (OUT_DIR / f"evaluation_report_{args.set}.md").write_text("\n".join(lines), encoding="utf-8")
    errors.to_csv(OUT_DIR / f"eval_errors_{args.set}.csv", index=False)
    print("\n".join(lines))
    print(f"\nSaved output/evaluation_report_{args.set}.md and output/eval_errors_{args.set}.csv")


if __name__ == "__main__":
    main()
