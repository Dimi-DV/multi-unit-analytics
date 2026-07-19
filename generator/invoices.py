"""AP invoice-line generation: COGS as purchases, derived from what the tickets
actually consumed (units x theoretical cost x waste), split across vendor cost
books and delivered on each vendor's fixed weekdays. Purchases respond to BOTH
menu mix and the planted beef price steps, so the Financial District COGS drift
emerges from parameters instead of pasted rows.

AP is a finance-side system: location codes are canonical throughout (the POS
re-key never reached the AP ledger); the bridge seed resolves both code eras.
"""

from datetime import date, timedelta

import numpy as np

from . import config, content, writers

INVOICE_HEADER = ["invoice_number", "line_number", "location_code", "vendor_name",
                  "invoice_date", "posted_date", "item_desc", "qty", "uom",
                  "unit_cost", "ext_cost"]

FOOD_KEYS = ("beef", "poultry", "seafood", "produce", "dairy", "dry", "coffee")
COST_CARD = {m.item_id: m.price_cents * m.fc_bp // 10000 for m in content.MENU}
UOM_TYPOS = {"CS": ("case", "Case"), "LB": ("lb",), "EA": ("ea",), "BG": ("bag",)}


def _week_dates(iso_year: int, iso_week: int) -> list[date]:
    return [date.fromisocalendar(iso_year, iso_week, wd) for wd in range(1, 8)]


def generate(rng: np.random.Generator, writer: writers.TableWriter, aggregates: dict) -> None:
    week_units = aggregates["week_units"]
    week_togo = aggregates["week_togo"]
    nulls = config.MESS_NULL_COSTS
    typos = config.MESS_TYPOS
    late = config.MESS_LATE

    # (loc, iso_year, iso_week) -> {item_id: units}
    by_week: dict[tuple, dict[int, int]] = {}
    for (loc_id, iy, iw, iid), units in week_units.items():
        by_week.setdefault((loc_id, iy, iw), {})[iid] = units

    seq: dict[str, int] = {}
    for loc in content.LOCATIONS:
        canon = loc.eras[0].code
        weeks = sorted(k for k in by_week if k[0] == loc.location_id)
        for (loc_id, iy, iw) in weeks:
            items = by_week[(loc_id, iy, iw)]
            wk_dates = [dt for dt in _week_dates(iy, iw)
                        if config.START_DATE <= dt <= config.END_DATE and dt >= loc.open_date]
            if not wk_dates:
                continue
            mid = wk_dates[len(wk_dates) // 2]

            demand = {k: 0 for k in content.COST_KEYS}
            for iid, units in sorted(items.items()):
                m = content.ITEM_BY_ID[iid]
                base = COST_CARD[iid]
                for ckey, share in sorted(m.split.items()):
                    amt = units * base * share
                    if ckey == "beef":
                        amt *= config.BEEF_STEPS.factor(mid)
                    demand[ckey] += int(amt)
            for k in FOOD_KEYS:
                demand[k] = int(demand[k] * config.WASTE_FACTOR)
            for k in ("na_bev", "bar"):
                demand[k] = int(demand[k] * 1.03)
            togo = week_togo.get((loc_id, iy, iw), 0)
            fmt = "counter_service" if loc.eras[-1].valid_from <= mid and loc.eras[-1].service_format == "counter_service" else loc.eras[0].service_format
            demand["packaging"] += togo * config.PACKAGING_PER_TOGO_TICKET[fmt]

            # weekly market noise per cost book, one draw each, fixed vendor order
            noise = {}
            for v in content.VENDORS:
                if v.category == "produce":
                    noise[v.category] = 1.0 + (rng.random() - 0.5) * 0.16
                elif v.category == "seafood":
                    noise[v.category] = 1.0 + (rng.random() - 0.5) * 0.24
                else:
                    noise[v.category] = 1.0

            for v in content.VENDORS:
                amount = demand[v.category]
                if amount < 2000:
                    continue
                days = [dt for dt in wk_dates if dt.isoweekday() in v.delivery_weekdays]
                if not days:
                    days = [wk_dates[0]]
                shares = rng.uniform(0.85, 1.15, size=len(days))
                shares = shares / shares.sum()
                catalog = content.VENDOR_CATALOG[v.category]
                cat_w = np.array([c[3] for c in catalog])
                cat_p = cat_w / cat_w.sum()

                for di, dt in enumerate(days):
                    inv_amount = int(amount * shares[di])
                    if inv_amount < 1000:
                        continue
                    seq[v.prefix] = seq.get(v.prefix, 0) + 1
                    inv_no = f"{v.prefix}{seq[v.prefix]:07d}"
                    m_lines = int(rng.integers(3, min(7, len(catalog)) + 1))
                    m_lines = min(m_lines, len(catalog))
                    picks = rng.choice(len(catalog), size=m_lines, replace=False, p=cat_p)
                    line_w = rng.uniform(0.6, 1.4, size=m_lines)
                    line_w = line_w / line_w.sum()

                    if late.invoice_quarter_end_only:
                        qtr_end = dt.month in (3, 6, 9, 12) and dt.day >= 21
                    else:
                        qtr_end = True
                    if qtr_end and rng.random() < late.invoice_rate:
                        posted = dt + timedelta(days=int(rng.integers(14, 36)))
                    else:
                        posted = dt + timedelta(days=int(rng.integers(0, 3)))

                    for ln, (pi, lw) in enumerate(zip(picks, line_w), start=1):
                        desc, uom, base_cost, _w, is_beef = catalog[int(pi)]
                        unit_cost = base_cost * noise[v.category]
                        if is_beef:
                            unit_cost *= config.BEEF_STEPS.factor(dt)
                        unit_cost = max(1, int(round(unit_cost)))
                        line_amt = int(inv_amount * lw)
                        qty_tenths = max(3, int(round(line_amt * 10 / unit_cost)))
                        ext = (qty_tenths * unit_cost + 5) // 10

                        uom_out = uom
                        if uom in UOM_TYPOS and rng.random() < typos.uom_rate:
                            opts = UOM_TYPOS[uom]
                            uom_out = opts[int(rng.random() * len(opts))]
                        cost_out = writers.money(unit_cost)
                        if (v.category == nulls.vendor_key and nulls.date_from <= dt <= nulls.date_to
                                and rng.random() < nulls.rate):
                            cost_out = ""

                        writer.write([inv_no, str(ln), canon, v.name, dt.isoformat(),
                                      posted.isoformat(), desc, writers.tenths(qty_tenths),
                                      uom_out, cost_out, writers.money(ext)])
