"""Load raw CSVs into Postgres: create schemas, run db/*.sql DDL, COPY every
seed and generated fact, print row counts.

Uses psycopg COPY FROM STDIN rather than `docker exec psql \\copy`: one code
path that behaves identically under PowerShell, Git Bash, macOS, Linux, and CI
(no shell-quoting regimes, no psql-on-host requirement).

Connection comes from PG* environment variables with docker-compose defaults:
  PGHOST=127.0.0.1 PGPORT=5433 PGUSER=mua PGPASSWORD=mua_local_dev PGDATABASE=mua
"""

import os
import sys

import psycopg

# (table, source dir, filename): explicit list, nothing walks a directory.
LOADS = [
    ("raw.pos_locations", "seeds", "pos_locations.csv"),
    ("raw.pos_menu_items", "seeds", "pos_menu_items.csv"),
    ("raw.ap_vendors", "seeds", "ap_vendors.csv"),
    ("raw.plan_budget", "seeds", "plan_budget.csv"),
    ("raw.ref_calendar", "seeds", "ref_calendar.csv"),
    ("raw.ref_dayparts", "seeds", "ref_dayparts.csv"),
    ("raw.ref_item_aliases", "seeds", "ref_item_aliases.csv"),
    ("raw.ref_location_bridge", "seeds", "ref_location_bridge.csv"),
    ("raw.pos_ticket_lines", "data/generated", "pos_ticket_lines.csv"),
    ("raw.ap_invoice_lines", "data/generated", "ap_invoice_lines.csv"),
    ("raw.labor_daily", "data/generated", "labor_daily.csv"),
    ("raw.gl_daily_sales", "data/generated", "gl_daily_sales.csv"),
]

DDL_FILES = ["db/10_raw_tables.sql"]


def conninfo() -> dict:
    return {
        "host": os.environ.get("PGHOST", "127.0.0.1"),
        "port": int(os.environ.get("PGPORT", "5433")),
        "user": os.environ.get("PGUSER", "mua"),
        "password": os.environ.get("PGPASSWORD", "mua_local_dev"),
        "dbname": os.environ.get("PGDATABASE", "mua"),
    }


def main() -> int:
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(root)
    with psycopg.connect(**conninfo()) as conn:
        with conn.cursor() as cur:
            for ddl in DDL_FILES:
                with open(ddl, "r", encoding="utf-8") as f:
                    cur.execute(f.read())
            print(f"DDL applied: {', '.join(DDL_FILES)}")

            total = 0
            for table, src, fname in LOADS:
                path = os.path.join(src, fname)
                if not os.path.exists(path):
                    print(f"MISSING {path}: run `python -m generator` first")
                    return 1
                cur.execute(f"TRUNCATE {table}")
                with open(path, "r", encoding="utf-8") as f, cur.copy(
                        f"COPY {table} FROM STDIN WITH (FORMAT csv, HEADER true)") as cp:
                    while chunk := f.read(1 << 20):
                        cp.write(chunk)
                cur.execute(f"SELECT count(*) FROM {table}")
                n = cur.fetchone()[0]
                total += n
                print(f"  {table}: {n:,} rows")
        conn.commit()
    print(f"load complete: {total:,} rows across {len(LOADS)} raw tables")
    return 0


if __name__ == "__main__":
    sys.exit(main())
