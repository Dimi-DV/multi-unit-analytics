"""Apply the SQL layers: sql/staging/*.sql then sql/marts/*.sql in lexical
order. Files that contain no executable statements yet (spec stubs are pure
comments) are reported and skipped, so this command stays runnable at every
stage of Phase 1.
"""

import os
import pathlib
import re
import sys

import psycopg

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from load import conninfo  # noqa: E402  (same directory)


def executable_sql(text: str) -> str:
    no_block = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    lines = [ln for ln in no_block.splitlines() if not ln.strip().startswith("--")]
    return "\n".join(lines).strip()


def main() -> int:
    root = pathlib.Path(__file__).resolve().parent.parent
    os.chdir(root)
    files = sorted((root / "sql" / "staging").glob("*.sql")) + \
        sorted((root / "sql" / "marts").glob("*.sql"))
    applied = skipped = 0
    with psycopg.connect(**conninfo()) as conn:
        for path in files:
            body = executable_sql(path.read_text(encoding="utf-8"))
            rel = path.relative_to(root)
            if not body:
                print(f"  stub, skipped: {rel}")
                skipped += 1
                continue
            with conn.cursor() as cur:
                cur.execute(path.read_text(encoding="utf-8"))
            conn.commit()   # per file: a late failure must not roll back built layers
            print(f"  applied: {rel}")
            applied += 1
    print(f"build: {applied} applied, {skipped} stubs skipped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
