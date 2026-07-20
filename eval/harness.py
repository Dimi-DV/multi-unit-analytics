"""Text-to-SQL evaluation run: python eval/harness.py [--schema marts|raw] [--limit N]

One attempt per question, no retries, no error-feedback loop: the measured
number must not hide a self-repair budget. Generated SQL executes in a
read-only session with a statement timeout; a cheap statement gate rejects
anything that is not a single SELECT/WITH before it reaches the database
(defense in depth on top of the read-only transaction; interactive agent
access goes through postgres-mcp restricted mode, see README.md).

Two ways to reach the subject model (--runner):
  api        Anthropic Messages API; requires ANTHROPIC_API_KEY.
  claude-cli Claude Code CLI headless mode (`claude -p`), billed to the
             developer's subscription. Integrity contract: every question is
             answered by a fresh process started in an empty temp directory
             with agentic turns capped at one, so the subject sees only the
             schema context and the question, never this repo or its answer
             key. Caveat recorded with the result: the CLI wraps the model in
             the Claude Code system prompt, so the measured subject is "model
             inside Claude Code", not the bare API model.

Without a usable runner this exits with instructions instead of inventing a
number. Results land in eval/results/ (gitignored); publishing a number in the
repo README is a deliberate, separate act that must include the failure-mode
analysis.
"""

import argparse
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

import psycopg
import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scoring import execution_match  # noqa: E402

MODEL_ID = "claude-sonnet-5"   # pinned; the published number names this id
HERE = pathlib.Path(__file__).parent


def conninfo():
    return {
        "host": os.environ.get("PGHOST", "127.0.0.1"),
        "port": int(os.environ.get("PGPORT", "5433")),
        "user": os.environ.get("PGUSER", "mua"),
        "password": os.environ.get("PGPASSWORD", "mua_local_dev"),
        "dbname": os.environ.get("PGDATABASE", "mua"),
        "options": "-c default_transaction_read_only=on -c statement_timeout=20000",
    }


def ask_cli(prompt: str, model: str) -> str:
    """One fresh, context-free `claude -p` process per question (see module doc)."""
    exe = shutil.which("claude")
    if exe is None:
        raise RuntimeError("claude CLI not found on PATH")
    workdir = tempfile.mkdtemp(prefix="mua-eval-")
    proc = subprocess.run(
        [exe, "-p", "--model", model, "--output-format", "text", "--max-turns", "1"],
        input=prompt, capture_output=True, text=True, encoding="utf-8",
        cwd=workdir, timeout=300)
    if proc.returncode != 0:
        raise RuntimeError(f"claude CLI exit {proc.returncode}: {proc.stderr.strip()[:300]}")
    return proc.stdout


def extract_sql(text: str) -> str:
    m = re.search(r"```(?:sql)?\s*(.*?)```", text, re.S)
    sql = (m.group(1) if m else text).strip().rstrip(";")
    return sql


def gate(sql: str) -> str | None:
    """Return a rejection reason, or None if the statement may run."""
    if ";" in sql:
        return "multiple statements"
    head = sql.lstrip().lower()
    if not (head.startswith("select") or head.startswith("with")):
        return "not a SELECT/WITH statement"
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--schema", choices=["marts", "raw"], default="marts",
                    help="which schema context the model gets (the comparison is the point)")
    ap.add_argument("--limit", type=int, default=0, help="run only the first N questions")
    ap.add_argument("--runner", choices=["api", "claude-cli"], default="api",
                    help="api (needs ANTHROPIC_API_KEY) or claude-cli (subscription)")
    args = ap.parse_args()

    client = None
    if args.runner == "api":
        if not os.environ.get("ANTHROPIC_API_KEY"):
            print("ANTHROPIC_API_KEY is not set. This harness measures a real model or")
            print("nothing at all; it never fabricates results. Set the key and re-run,")
            print("or use --runner claude-cli to bill the Claude Code subscription.")
            return 2
        import anthropic  # imported late so the no-key path needs no SDK
        client = anthropic.Anthropic()
    elif shutil.which("claude") is None:
        print("--runner claude-cli needs the claude CLI on PATH.")
        return 2

    ctx_file = "schema_context.md" if args.schema == "marts" else "schema_context_raw.md"
    schema_ctx = (HERE / ctx_file).read_text(encoding="utf-8")
    bank = yaml.safe_load((HERE / "bank.yaml").read_text(encoding="utf-8"))
    if args.limit:
        bank = bank[: args.limit]

    results = []
    with psycopg.connect(**conninfo()) as conn:
        for q in bank:
            prompt = (f"{schema_ctx}\n\nWrite one PostgreSQL query answering this "
                      f"question. Return only the SQL, nothing else.\n\n"
                      f"Question: {q['question']}")
            if args.runner == "api":
                msg = client.messages.create(model=MODEL_ID, max_tokens=1500,
                                             messages=[{"role": "user", "content": prompt}])
                raw = msg.content[0].text
            else:
                raw = ask_cli(prompt, MODEL_ID)
            sql = extract_sql(raw)
            rec = {"id": q["id"], "difficulty": q["difficulty"],
                   "question": q["question"], "generated_sql": sql}

            reason = gate(sql)
            if reason:
                rec.update(passed=False, failure_mode=f"gated: {reason}")
            else:
                with conn.cursor() as cur:
                    cur.execute(q["canonical_sql"])
                    expected = cur.fetchall()
                try:
                    with conn.cursor() as cur:
                        cur.execute(sql)
                        actual = cur.fetchall()
                    ok = execution_match(expected, actual, q.get("match") == "ordered")
                    rec.update(passed=ok,
                               failure_mode=None if ok else "wrong result set")
                except psycopg.Error as e:
                    conn.rollback()
                    rec.update(passed=False,
                               failure_mode=f"execution error: {type(e).__name__}")
            results.append(rec)
            print(f"  {q['id']}: {'PASS' if rec['passed'] else 'FAIL (' + str(rec['failure_mode']) + ')'}")

    out_dir = HERE / "results"
    out_dir.mkdir(exist_ok=True)
    passed = sum(r["passed"] for r in results)
    summary = {"model": MODEL_ID, "schema_condition": args.schema,
               "runner": args.runner,
               "runner_note": (None if args.runner == "api" else
                               "claude-cli headless: subject ran inside the Claude Code "
                               "system prompt, fresh context-free process per question"),
               "passed": passed, "total": len(results),
               "accuracy": round(passed / len(results), 4), "results": results}
    out = out_dir / f"results_{args.schema}.json"
    out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\n{passed}/{len(results)} execution-match on schema={args.schema}")
    print(f"written: {out} (publishing a number in the README requires the "
          f"failure-mode analysis to go with it)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
