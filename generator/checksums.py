"""SHA-256 manifest for the generated fact files.

The manifest is committed (seeds/manifest.sha256); the facts themselves are
not. Byte-identity is enforced by checksum instead of by committing ~450MB.
Files are hashed from an explicit sorted list; nothing walks a directory
(directory iteration order differs across filesystems and would be a
determinism hazard). The manifest is parsed with splitlines() so a CRLF
checkout can never produce a false verification failure.
"""

import hashlib

from . import config


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1 << 20):
            h.update(chunk)
    return h.hexdigest()


def write_manifest(out_dir: str, seeds_dir: str) -> None:
    lines = [f"{_sha256(f'{out_dir}/{name}')}  {name}" for name in sorted(config.FACT_FILES)]
    with open(f"{seeds_dir}/manifest.sha256", "w", newline="", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def verify(out_dir: str, seeds_dir: str) -> list[str]:
    """Return a list of mismatch descriptions; empty list means verified."""
    problems = []
    with open(f"{seeds_dir}/manifest.sha256", "r", encoding="utf-8") as f:
        entries = [ln.split() for ln in f.read().splitlines() if ln.strip()]
    manifest = {name: digest for digest, name in entries}
    if set(manifest) != set(config.FACT_FILES):
        problems.append(f"manifest file set {sorted(manifest)} != expected {sorted(config.FACT_FILES)}")
        return problems
    for name in sorted(config.FACT_FILES):
        actual = _sha256(f"{out_dir}/{name}")
        if actual != manifest[name]:
            problems.append(f"{name}: manifest {manifest[name][:12]}... != actual {actual[:12]}...")
    return problems
