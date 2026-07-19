"""Determinism guard: fail if generator code contains anything that could make
two runs differ. Broader than wall-clock alone: hash-order, directory-order,
process-entropy, and ambient-RNG hazards are all byte-identity killers.

Guard scripts themselves are not byte-pinned, so this file may glob; the
generator itself must never walk a directory.
"""

import pathlib
import re
import sys

SCAN = sorted(pathlib.Path("generator").glob("*.py")) + [pathlib.Path("scripts/load.py")]

BANNED = [
    (re.compile(r"\.now\(|\.today\(|utcnow|time\.time|monotonic|perf_counter"), "wall clock"),
    (re.compile(r"^\s*import time|^\s*from time", re.M), "time module"),
    (re.compile(r"(?<![\w.])random\."), "stdlib random (only the passed PCG64 Generator is allowed)"),
    (re.compile(r"^\s*import random|^\s*from random", re.M), "stdlib random import"),
    (re.compile(r"uuid"), "uuid"),
    (re.compile(r"default_rng\("), "unseeded default_rng"),
    (re.compile(r"listdir|iterdir|scandir|os\.walk|glob\.|\.glob\("), "directory iteration"),
    (re.compile(r"PYTHONHASHSEED"), "hash-seed dependence"),
]

failures = []
for path in SCAN:
    text = path.read_text(encoding="utf-8")
    for pattern, why in BANNED:
        for m in pattern.finditer(text):
            line = text.count("\n", 0, m.start()) + 1
            failures.append(f"{path}:{line}: {why} ({m.group(0)!r})")

if failures:
    print("DETERMINISM GUARD FAIL:")
    for f in failures:
        print(" ", f)
    sys.exit(1)
print(f"determinism guard OK: {len(SCAN)} files clean")
