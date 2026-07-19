"""Content guard for tracked files. Two checks:

1. Banned tokens, compared as SHA-256 hashes of lowercase words so this guard
   never contains the strings it bans.
2. Em-dashes (U+2014): banned in every tracked file (project writing rule for
   anything an employer might read).
"""

import hashlib
import subprocess
import sys

BANNED_HASHES = {
    # sha256(lowercase token)
    "af1934f0c1e7a47ce59ef640b27bb3adcec5bd37e1ea0dd9c59982a5b9c7fb7d",
    "d52a2de4848d2a86d4f25a1ce52f6601042d04b435b97ddf03101372e8d6759b",
    "4c3280c17f9d982ccbac882ae1f48dad224dba938bee87bf18e31c76b0c3b88b",
}

files = subprocess.run(["git", "ls-files"], capture_output=True, text=True,
                       check=True).stdout.splitlines()
failures = []
for path in files:
    try:
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
    except (UnicodeDecodeError, FileNotFoundError):
        continue
    em = chr(0x2014)
    if em in text:
        line = text.split(em)[0].count("\n") + 1
        failures.append(f"{path}:{line}: em-dash")
    word = []
    for ch in text.lower() + " ":
        if ch.isalpha():
            word.append(ch)
        elif word:
            token = "".join(word)
            word = []
            if hashlib.sha256(token.encode()).hexdigest() in BANNED_HASHES:
                failures.append(f"{path}: banned token (hash match)")
if failures:
    print("CONTENT GUARD FAIL:")
    for f in sorted(set(failures)):
        print(" ", f)
    sys.exit(1)
print(f"content guard OK: {len(files)} tracked files clean")
