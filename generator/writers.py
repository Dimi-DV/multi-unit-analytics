"""CSV rendering rules. Every byte written to disk goes through this module.

LF discipline on Windows requires BOTH newline='' on open() AND
lineterminator='\\n' on csv.writer: without the first, Python translates \\n to
\\r\\n on Windows; separately, csv.writer's default lineterminator is \\r\\n on
every platform. The SHA-256 manifest hashes working-tree bytes, so the writer
must emit LF itself; .gitattributes is only the second line of defense.

Money is integer cents end to end. The renderer is sign-aware because Python
floor division corrupts negatives: -1234 // 100 == -13 and -1234 % 100 == 66.
"""

import csv
from datetime import datetime, timedelta

from . import config


def money(cents: int) -> str:
    sign = "-" if cents < 0 else ""
    d, r = divmod(abs(cents), 100)
    return f"{sign}{d}.{r:02d}"


def tenths(t: int) -> str:
    sign = "-" if t < 0 else ""
    d, r = divmod(abs(t), 10)
    return f"{sign}{d}.{r}"


def _golden_asserts() -> None:
    assert money(-1234) == "-12.34"
    assert money(1234) == "12.34"
    assert money(-5) == "-0.05"
    assert money(5) == "0.05"
    assert money(0) == "0.00"
    assert money(-100) == "-1.00"
    assert tenths(-15) == "-1.5"
    assert tenths(305) == "30.5"


_golden_asserts()


def fmt_ts_local(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def utc_offset_hours(dt: datetime) -> int:
    off = config.BASE_UTC_OFFSET
    for t, o in config.DST_TRANSITIONS:
        if dt >= t:
            off = o
    return off


def fmt_ts_utc(dt: datetime) -> str:
    """Render a naive America/New_York local time as UTC ISO-8601 Z.

    The fall-back ambiguous hour is never emitted in a UTC window (the only
    UTC window is Mar-May 2025), so first-offset resolution is safe.
    """
    utc = dt - timedelta(hours=utc_offset_hours(dt))
    return utc.strftime("%Y-%m-%dT%H:%M:%SZ")


class TableWriter:
    """Streaming CSV writer that also captures the committed sample extract."""

    def __init__(self, path: str, header: list[str], sample_path: str | None = None,
                 sample_rows: int = config.SAMPLES_ROWS):
        self._f = open(path, "w", newline="", encoding="utf-8")
        self._w = csv.writer(self._f, lineterminator="\n")
        self._w.writerow(header)
        self._header = header
        self._sample_path = sample_path
        self._sample_rows = sample_rows
        self._sample: list[list[str]] = []
        self.count = 0

    def write(self, row: list) -> None:
        self._w.writerow(row)
        if self._sample_path and len(self._sample) < self._sample_rows:
            self._sample.append(row)
        self.count += 1

    def close(self) -> None:
        self._f.close()
        if self._sample_path:
            with open(self._sample_path, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f, lineterminator="\n")
                w.writerow(self._header)
                w.writerows(self._sample)


def write_seed(path: str, header: list[str], rows: list[list]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(header)
        w.writerows(rows)
