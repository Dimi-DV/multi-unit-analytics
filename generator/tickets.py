"""POS ticket-line generation. One chunk per (location, day), locations in id
order, days in date order: the RNG draw order is part of the determinism
contract, so the loop structure and the order of draws inside a day are fixed.

Planted scenarios adjust generation parameters before drawing (never pasted
rows); the mess transforms at the end of each day are the only post-hoc edits,
and they only touch how rows RENDER (the canonical aggregates for GL/labor/
invoices are computed before mess is applied).
"""

from datetime import date, datetime, timedelta

import numpy as np

from . import caldata, config, content, writers

TICKET_HEADER = ["location_code", "business_date", "ticket_number", "line_number",
                 "closed_at", "item_name", "qty", "unit_price", "discount_amount",
                 "line_state", "order_mode"]

DAYPART_ORDER = ["breakfast", "lunch", "afternoon", "dinner", "late_night"]
DAYPART_SPAN = {"breakfast": (7 * 60, 240), "lunch": (11 * 60, 240),
                "afternoon": (15 * 60, 120), "dinner": (17 * 60, 300),
                "late_night": (22 * 60, 240)}   # late night wraps past midnight
FOOD_CATS = content.CATEGORIES[:7]
NA_IDS = [40, 41, 42, 43]
BAR_IDS = [44, 45, 46]
STATES = ["sale", "void", "comp", "refund"]


def _round50(cents_x100: int) -> int:
    return ((cents_x100 + 2500) // 5000) * 50


PRICE_1 = {m.item_id: m.price_cents for m in content.MENU}
PRICE_2 = {m.item_id: (m.price_cents if m.held_at_round else _round50(m.price_cents * 103))
           for m in content.MENU}
ITEM = {m.item_id: m for m in content.MENU}


def price_on(item_id: int, d: date) -> int:
    return PRICE_2[item_id] if d >= config.PRICE_ROUND_DATE else PRICE_1[item_id]


class EraTables:
    """Per-(era, month) item pools with normalized weights, built deterministically."""

    def __init__(self, era: content.Era, month: int):
        allowed = content.EXPRESS_ITEM_IDS if era.service_format == "counter_service" else None
        self.cat_pools = []
        for cat in FOOD_CATS:
            ids, w = [], []
            for m in content.MENU:
                if m.category != cat:
                    continue
                if allowed is not None and m.item_id not in allowed:
                    continue
                if m.seasonal_months and month not in m.seasonal_months:
                    continue
                ids.append(m.item_id)
                w.append(content.POPULARITY_WEIGHT[m.tier] * era.item_bias.get(m.item_id, 1.0))
            arr = np.array(w, dtype=np.float64)
            self.cat_pools.append((np.array(ids, dtype=np.int64), arr / arr.sum()))
        na_w = np.array([content.POPULARITY_WEIGHT[ITEM[i].tier] for i in NA_IDS])
        self.na = (np.array(NA_IDS, dtype=np.int64), na_w / na_w.sum())
        bar_w = np.array([content.POPULARITY_WEIGHT[ITEM[i].tier] for i in BAR_IDS])
        self.bar = (np.array(BAR_IDS, dtype=np.int64), bar_w / bar_w.sum())


def _era_for(loc: content.Location, d: date) -> content.Era:
    for era in loc.eras:
        if era.valid_from <= d and (era.valid_to is None or d <= era.valid_to):
            return era
    raise ValueError(f"no era for location {loc.location_id} on {d}")


def _daypart_probs(era: content.Era, weekend: bool) -> np.ndarray:
    w = era.daypart_w_we if weekend else era.daypart_w_wd
    arr = np.array([w[dp] for dp in DAYPART_ORDER], dtype=np.float64)
    return arr / arr.sum()


def _cat_probs(daypart: str, brunch: bool) -> np.ndarray:
    key = "brunch" if (brunch and daypart == "lunch") else daypart
    arr = np.array(config_CAT_W[key], dtype=np.float64)
    return arr / arr.sum()


config_CAT_W = content.CAT_W


def expected_tickets(loc: content.Location, era: content.Era, d: date, cal: dict) -> float:
    rec = cal[d]
    if rec["holiday_name"] in config.CLOSED_HOLIDAYS:
        return 0.0
    lam = era.base_weekday_tickets
    if rec["is_weekend"]:
        lam *= era.weekend_mult
    lam *= content.MONTH_SEASONALITY[d.month] * loc.month_seas_overrides.get(d.month, 1.0)
    lam *= content.YEAR_TRAFFIC[d.year]
    if rec["holiday_name"]:
        base, over = caldata.HOLIDAY_DEMAND.get(rec["holiday_name"], (1.0, {}))
        lam *= over.get(loc.location_id, base)
    if rec["is_dining_week"] and era.service_format == "full_service" and loc.borough == "Manhattan":
        lam *= 1.12
    if rec["is_school_break"] and loc.location_id in (2, 7) and not rec["is_weekend"]:
        lam *= 0.94
    if loc.location_id == 9:   # Astoria ramp
        weeks_open = (d - loc.open_date).days / 7.0
        r = config.AST_RAMP
        if weeks_open < r.honeymoon_weeks:
            lam *= r.honeymoon_mult
        elif weeks_open < r.honeymoon_weeks + r.dip_weeks:
            lam *= r.dip_mult
        else:
            t = min(1.0, (weeks_open - r.honeymoon_weeks - r.dip_weeks) / r.ramp_to_one_weeks)
            lam *= r.dip_mult + (1.0 - r.dip_mult) * t
    return lam


def _comp_rate(loc_id: int, d: date) -> float:
    for s in config.COMP_SPIKES:
        if s.location_id == loc_id and s.year == d.year and s.month == d.month:
            return s.comp_rate
    return config.MESS_STATES.comp_rate


def _dup_rate(loc_id: int, d: date) -> float:
    for w in config.DUP_WINDOWS:
        if (w.location_id is None or w.location_id == loc_id) and w.date_from <= d <= w.date_to:
            return w.rate
    return 0.0


def _bdate_fmt(loc_id: int, d: date) -> str:
    for w in config.DATE_FORMAT_WINDOWS:
        if w.location_id == loc_id and w.date_from <= d <= w.date_to:
            return d.strftime(w.fmt)
    return d.isoformat()


def _closed_fmt(loc_id: int, d: date, dt: datetime) -> str:
    w = config.MESS_UTC_WINDOW
    if loc_id == w.location_id and w.date_from <= d <= w.date_to:
        return writers.fmt_ts_utc(dt)
    return writers.fmt_ts_local(dt)


def generate(rng: np.random.Generator, writer: writers.TableWriter,
             cal: dict, aggregates: dict) -> None:
    daily_net = aggregates["daily_net"]
    week_units = aggregates["week_units"]
    week_togo = aggregates["week_togo"]
    outlier_by_key = {(o.location_id, o.day): o for o in config.OUTLIERS}
    drift = config.MESS_NAME_DRIFT
    late = config.MESS_LATE
    states_cfg = config.MESS_STATES

    for loc in content.LOCATIONS:
        seq = {era.code: era.ticket_seq_start for era in loc.eras}
        tables_cache: dict[tuple, EraTables] = {}
        d = max(config.START_DATE, loc.open_date)
        while d <= config.END_DATE:
            era = _era_for(loc, d)
            key = (era.code, d.month)
            if key not in tables_cache:
                tables_cache[key] = EraTables(era, d.month)
            tables = tables_cache[key]
            rec = cal[d]
            weekend = rec["is_weekend"]

            lam = expected_tickets(loc, era, d, cal)
            n = int(rng.poisson(lam)) if lam > 0 else 0
            if n == 0:
                d += timedelta(days=1)
                continue

            dp_idx = rng.choice(5, size=n, p=_daypart_probs(era, weekend))
            frac = rng.random(n)
            comp_p = _comp_rate(loc.location_id, d)
            nl_lam = max(era.avg_food_lines - 1.0, 0.05)
            n_food = np.minimum(rng.poisson(nl_lam, size=n) + 1, 7)

            # absolute minute of day (late night runs past 1440); tickets are then
            # numbered in time order so ticket_number correlates with closed_at
            start = np.array([DAYPART_SPAN[DAYPART_ORDER[i]][0] for i in dp_idx])
            span = np.array([DAYPART_SPAN[DAYPART_ORDER[i]][1] for i in dp_idx])
            minute = start + (frac * span).astype(np.int64)
            order = np.argsort(minute, kind="stable")
            seconds = rng.integers(0, 60, size=n)

            # per-daypart category draws, then per-category item draws (fixed order)
            cats = np.zeros(int(n_food.sum()), dtype=np.int64)
            line_dp = np.repeat(dp_idx, n_food)
            pos = 0
            starts = np.concatenate(([0], np.cumsum(n_food)))
            for di, dp in enumerate(DAYPART_ORDER):
                mask = line_dp == di
                cnt = int(mask.sum())
                if cnt:
                    cats[mask] = rng.choice(7, size=cnt, p=_cat_probs(dp, weekend))
            items = np.zeros_like(cats)
            for ci in range(7):
                mask = cats == ci
                cnt = int(mask.sum())
                if cnt:
                    ids, probs = tables.cat_pools[ci]
                    items[mask] = rng.choice(ids, size=cnt, p=probs)

            qty = rng.choice(np.array([1, 2, 3]), size=len(items), p=[0.90, 0.09, 0.01])
            sale_p = 1.0 - states_cfg.void_rate - comp_p - states_cfg.refund_rate
            state_idx = rng.choice(4, size=len(items),
                                   p=[sale_p, states_cfg.void_rate, comp_p, states_cfg.refund_rate])
            disc_mask = rng.random(len(items)) < 0.05
            disc_pct = rng.uniform(0.10, 0.25, size=len(items))
            na_mask = rng.random(n) < era.na_attach
            na_items = rng.choice(tables.na[0], size=n, p=tables.na[1])
            bar_mask = rng.random(n) < era.bar_attach
            bar_items = rng.choice(tables.bar[0], size=n, p=tables.bar[1])
            mode_idx = rng.choice(3, size=n, p=list(era.order_mode_p))

            month_end = (d + timedelta(days=late.ticket_window_days)).month != d.month
            late_mask = rng.random(n) < (late.ticket_rate if month_end else 0.0)
            late_days = rng.integers(1, 3, size=n)
            dup_rate = _dup_rate(loc.location_id, d)
            dup_mask = rng.random(n) < dup_rate
            dup_delta = rng.integers(45, 181, size=n)

            # drift draws sized to worst case (every line), consumed in line order
            drift_roll = rng.random(len(items))
            drift_pick = rng.random(len(items))

            iso_y, iso_w, _ = d.isocalendar()
            gcx_hot = (era.code == "CW-GCX" and
                       (d.year, d.month) < (2025, 7 + drift.gcx_hot_months))
            drift_rate = drift.gcx_rate if gcx_hot else drift.rate

            day_rows = []
            net_day = 0
            bdate_s = _bdate_fmt(loc.location_id, d)
            code = era.code
            outlier = outlier_by_key.get((loc.location_id, d))
            outlier_done = False

            for k in range(n):
                ti = int(order[k])
                seq[code] += 1
                tno = seq[code]
                m = int(minute[ti])
                closed = datetime(d.year, d.month, d.day) + timedelta(minutes=m, seconds=int(seconds[ti]))
                if late_mask[ti]:
                    closed += timedelta(days=int(late_days[ti]))
                mode = ("DI", "TO", "DL")[int(mode_idx[ti])]
                if mode != "DI":
                    week_togo[(loc.location_id, iso_y, iso_w)] = week_togo.get((loc.location_id, iso_y, iso_w), 0) + 1

                lines = []
                a, b = int(starts[ti]), int(starts[ti + 1])
                for j in range(a, b):
                    iid = int(items[j])
                    st = STATES[int(state_idx[j])]
                    q = int(qty[j]) if st != "refund" else -1
                    lines.append((iid, q, st, bool(disc_mask[j]), float(disc_pct[j]), j))
                if na_mask[ti]:
                    lines.append((int(na_items[ti]), 1, "sale", False, 0.0, -1))
                if bar_mask[ti] and DAYPART_ORDER[int(dp_idx[ti])] in ("dinner", "late_night"):
                    lines.append((int(bar_items[ti]), 1, "sale", False, 0.0, -1))

                ticket_rows = []
                for ln, (iid, q, st, has_disc, pct, j) in enumerate(lines, start=1):
                    p = price_on(iid, d)
                    gross = q * p
                    disc = 0
                    if st == "sale" and has_disc and q > 0:
                        disc = int(round(gross * pct))
                    if st == "sale":
                        net_day += gross - disc
                    elif st == "refund":
                        net_day += gross
                    if st in ("sale", "comp") and q > 0:
                        wk = (loc.location_id, iso_y, iso_w, iid)
                        week_units[wk] = week_units.get(wk, 0) + q

                    name = ITEM[iid].name
                    if j >= 0 and iid in content.DRIFT_VARIANTS and drift_roll[j] < drift_rate:
                        variants = content.DRIFT_VARIANTS[iid]
                        if era.code == "CW-GCX" and iid in content.DRIFT_VARIANTS_GCX:
                            variants = variants + content.DRIFT_VARIANTS_GCX[iid]
                        name = variants[int(drift_pick[j] * len(variants))]

                    q_out, p_out, disc_out = q, p, disc
                    if outlier is not None and not outlier_done and st == "sale" and j >= 0:
                        if outlier.field == "unit_price":
                            p_out = outlier.value
                        elif outlier.field == "qty":
                            q_out = outlier.value
                        else:
                            disc_out = outlier.value
                        outlier_done = True

                    ticket_rows.append([code, bdate_s, str(tno), str(ln),
                                        _closed_fmt(loc.location_id, d, closed), name,
                                        str(q_out), writers.money(p_out), writers.money(disc_out),
                                        st, mode])
                day_rows.extend(ticket_rows)

                if dup_mask[ti]:   # re-fired ticket: same business key, later closed_at
                    reclosed = closed + timedelta(seconds=int(dup_delta[ti]))
                    for r in ticket_rows:
                        r2 = list(r)
                        r2[4] = _closed_fmt(loc.location_id, d, reclosed)
                        day_rows.append(r2)

            for row in day_rows:
                writer.write(row)
            dk = (loc.location_id, d)
            daily_net[dk] = daily_net.get(dk, 0) + net_day
            d += timedelta(days=1)
