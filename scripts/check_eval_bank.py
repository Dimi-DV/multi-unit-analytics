"""Answer-key guard: every canonical query in eval/bank.yaml must execute
read-only against the built marts and return at least one row. A broken
canonical query would silently misgrade the model it is supposed to measure.
"""

import os
import pathlib
import sys

import psycopg
import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent


def conninfo():
    return {
        "host": os.environ.get("PGHOST", "127.0.0.1"),
        "port": int(os.environ.get("PGPORT", "5433")),
        "user": os.environ.get("PGUSER", "mua"),
        "password": os.environ.get("PGPASSWORD", "mua_local_dev"),
        "dbname": os.environ.get("PGDATABASE", "mua"),
        "options": "-c default_transaction_read_only=on -c statement_timeout=30000",
    }


def main() -> int:
    bank = yaml.safe_load((ROOT / "eval" / "bank.yaml").read_text(encoding="utf-8"))
    failures = []
    with psycopg.connect(**conninfo()) as conn:
        for q in bank:
            try:
                with conn.cursor() as cur:
                    cur.execute(q["canonical_sql"])
                    rows = cur.fetchall()
                if not rows:
                    failures.append(f"{q['id']}: returned zero rows")
            except psycopg.Error as e:
                conn.rollback()
                failures.append(f"{q['id']}: {type(e).__name__}: {e}")
    if failures:
        print("EVAL BANK GUARD FAIL:")
        for f in failures:
            print(" ", f)
        return 1
    print(f"eval bank guard OK: {len(bank)} canonical queries execute and return rows")
    return 0


if __name__ == "__main__":
    sys.exit(main())
