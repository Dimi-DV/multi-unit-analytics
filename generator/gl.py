"""GL daily sales: finance's book, derived from the canonical net-sales rule
(sale lines net of discounts, refunds negative, voids and comps excluded,
duplicates counted once, outlier mis-keys posted corrected). Outside the
planted variance windows, GL ties to cleaned POS net sales to the penny; that
is the contract the owner's tie-out query (analysis 09) validates against.
"""

from datetime import date, timedelta

import numpy as np

from . import config, content, writers

GL_HEADER = ["business_date", "location_code", "gl_net_sales"]


def generate(rng: np.random.Generator, writer: writers.TableWriter, aggregates: dict) -> None:
    daily_net = aggregates["daily_net"]

    for loc in content.LOCATIONS:
        canon = loc.eras[0].code
        days = sorted(d for (lid, d) in daily_net if lid == loc.location_id)
        gl = {d: daily_net[(loc.location_id, d)] for d in days}

        for w in config.GL_WINDOWS:
            if w.location_id != loc.location_id:
                continue
            wdays = [d for d in days if w.date_from <= d <= w.date_to]
            if w.mode == "deposit_shift":
                for d in wdays:
                    if d.weekday() in (4, 5, 6):   # Fri/Sat/Sun post with Monday's deposit
                        target = d + timedelta(days=(7 - d.weekday()))
                        while target not in gl and target <= config.END_DATE:
                            target += timedelta(days=1)
                        if target in gl and target != d:
                            gl[target] += gl[d]
                            gl[d] = 0
            elif w.mode == "missing_day":
                mid = wdays[len(wdays) // 2]
                nxt = mid + timedelta(days=1)
                if nxt in gl:
                    gl[nxt] += gl[mid]
                    gl[mid] = 0
            elif w.mode == "rounding":
                for d in wdays:
                    delta = int(rng.integers(-300, 301))
                    if delta == 0:
                        delta = 137
                    gl[d] += delta

        for d in days:
            writer.write([d.isoformat(), canon, writers.money(gl[d])])
