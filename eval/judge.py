"""Secondary LLM-as-judge plus its calibration protocol.

The judge classifies execution-match FAILURES (semantic near-miss vs schema
linking miss vs ambiguity vs hallucination) and never overrides the primary
metric. Before any judge output is quoted, its human-agreement rate must be
measured: `--export-sheet` writes a blind hand-scoring CSV; after the human
column is filled in, `--agreement` computes agreement. A judge quoted without
that rate is an unmeasured instrument.
"""

import argparse
import csv
import json
import os
import pathlib
import sys

MODEL_ID = "claude-opus-4-8"   # judge is pinned separately from the subject model
HERE = pathlib.Path(__file__).parent

JUDGE_PROMPT = """You are auditing a text-to-SQL failure. Given the question, the
generated SQL, and the canonical SQL, classify the failure as exactly one of:
semantic_near_miss (right idea, small logic slip), schema_linking (wrong
table/column/join), ambiguity (the question admits the produced reading),
hallucination (invented objects or syntax), other. Respond as JSON:
{"category": "...", "explanation": "one sentence"}.

Question: {question}
Generated SQL:
{generated}
Canonical SQL:
{canonical}
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default=str(HERE / "results" / "results_marts.json"))
    ap.add_argument("--export-sheet", action="store_true",
                    help="write the blind hand-scoring sheet for calibration")
    ap.add_argument("--agreement", metavar="SHEET",
                    help="compute judge vs human agreement from a filled sheet")
    args = ap.parse_args()

    if args.agreement:
        with open(args.agreement, newline="", encoding="utf-8") as f:
            rows = [r for r in csv.DictReader(f) if r.get("human_category", "").strip()]
        if not rows:
            print("no filled human_category rows found")
            return 1
        agree = sum(r["judge_category"] == r["human_category"] for r in rows)
        print(f"judge-human agreement: {agree}/{len(rows)} = {agree / len(rows):.0%} "
              f"(quote this next to any judge output)")
        return 0

    data = json.loads(pathlib.Path(args.results).read_text(encoding="utf-8"))
    failures = [r for r in data["results"] if not r["passed"]]
    if not failures:
        print("no failures to judge")
        return 0

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ANTHROPIC_API_KEY is not set; the judge measures or stays silent.")
        return 2
    import anthropic
    import yaml

    bank = {q["id"]: q for q in yaml.safe_load((HERE / "bank.yaml").read_text(encoding="utf-8"))}
    client = anthropic.Anthropic()
    judged = []
    for r in failures:
        prompt = JUDGE_PROMPT.format(question=r["question"],
                                     generated=r["generated_sql"],
                                     canonical=bank[r["id"]]["canonical_sql"])
        msg = client.messages.create(model=MODEL_ID, max_tokens=300,
                                     messages=[{"role": "user", "content": prompt}])
        try:
            verdict = json.loads(msg.content[0].text.strip().strip("`"))
        except json.JSONDecodeError:
            verdict = {"category": "unparseable_judge_output", "explanation": ""}
        judged.append({**r, "judge_category": verdict.get("category", ""),
                       "judge_explanation": verdict.get("explanation", "")})
        print(f"  {r['id']}: {verdict.get('category')}")

    out = HERE / "results" / "judged_failures.json"
    out.write_text(json.dumps(judged, indent=2), encoding="utf-8")
    print(f"written: {out}")

    if args.export_sheet:
        sheet = HERE / "results" / "hand_scoring_sheet.csv"
        with open(sheet, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f, lineterminator="\n")
            w.writerow(["id", "question", "generated_sql", "canonical_sql",
                        "judge_category", "human_category"])
            for r in judged:
                w.writerow([r["id"], r["question"], r["generated_sql"],
                            bank[r["id"]]["canonical_sql"], r["judge_category"], ""])
        print(f"hand-scoring sheet: {sheet} (fill human_category, then --agreement)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
