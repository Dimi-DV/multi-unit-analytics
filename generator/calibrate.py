"""Calibration checker: python -m generator.calibrate

Recomputes the four planted-storyline metrics FROM THE GENERATED FILES (mess
and all, applying the canonical cleaning rules: dedup-keep-latest, voids/comps
excluded, refunds negative) and fails if any lands outside its tolerance band.
This is what keeps README/memo numbers honest: the spec states bands, the memo
transcribes measured output, and CI refuses a dataset whose story drifted.

Bands (config.py): A. Financial District trailing-12 prime-cost miss vs the
60.0 target; B. rolling-4-week prime>62 streak length and dominance;
C. naive-vs-comp H1-2026 YoY spread; D. NA-beverage attach gap.
"""

import csv
import sys
from datetime import date, timedelta

from . import config

FIDI = 5
T12_FROM, T12_TO = date(2025, 7, 1), date(2026, 6, 30)


def parse_date(s: str) -> date:
    s = s.strip()
    if "/" in s:
        a, b, c = s.split("/")
        if len(a) == 4:                      # YYYY/MM/DD
            return date(int(a), int(b), int(c))
        return date(int(c), int(a), int(b))  # M/D/YYYY
    return date(int(s[0:4]), int(s[5:7]), int(s[8:10]))


def parse_cents(s: str) -> int:
    s = s.strip()
    if not s:
        return 0
    neg = s.startswith("-")
    if neg:
        s = s[1:]
    d, _, r = s.partition(".")
    return (-1 if neg else 1) * (int(d) * 100 + int((r + "00")[:2]))


def load_seeds(seeds: str):
    with open(f"{seeds}/ref_location_bridge.csv", newline="", encoding="utf-8") as f:
        bridge = {r["location_code"]: int(r["location_id"]) for r in csv.DictReader(f)}
    with open(f"{seeds}/pos_menu_items.csv", newline="", encoding="utf-8") as f:
        cat = {int(r["menu_item_id"]): r["category"].strip().lower() for r in csv.DictReader(f)}
    na_ids = {i for i, c in cat.items() if c == "na beverages"}
    with open(f"{seeds}/ref_item_aliases.csv", newline="", encoding="utf-8") as f:
        alias = {r["alias"].strip().lower(): int(r["menu_item_id"]) for r in csv.DictReader(f)}
    with open(f"{seeds}/pos_locations.csv", newline="", encoding="utf-8") as f:
        loc_rows = list(csv.DictReader(f))
    return bridge, alias, na_ids, loc_rows


def scan_tickets(path: str, bridge: dict, alias: dict, na_ids: set):
    daily_net: dict[tuple, int] = {}
    attach: dict[int, list] = {}          # loc -> [tickets, na_tickets] in T12 window
    comp_month: dict[tuple, list] = {}    # (loc, y, m) -> [comp_cents, net_cents]

    cur_key = None
    day_lines: dict[tuple, tuple] = {}

    def flush():
        if cur_key is None or not day_lines:
            return
        code, bd = cur_key
        loc = bridge[code]
        net = 0
        comp = 0
        tickets: dict[str, list] = {}
        for (tno, lno), (closed, item, qty, price, disc, state) in day_lines.items():
            t = tickets.setdefault(tno, [False, False])
            if state == "sale":
                net += qty * price - disc
                t[0] = True
                iid = alias.get(item.strip().lower())
                if iid in na_ids:
                    t[1] = True
            elif state == "refund":
                net += qty * price
            elif state == "comp":
                comp += abs(qty) * price
        daily_net[(loc, bd)] = daily_net.get((loc, bd), 0) + net
        cm = comp_month.setdefault((loc, bd.year, bd.month), [0, 0])
        cm[0] += comp
        cm[1] += net
        if T12_FROM <= bd <= T12_TO:
            a = attach.setdefault(loc, [0, 0])
            for has_sale, has_na in tickets.values():
                if has_sale:
                    a[0] += 1
                    if has_na:
                        a[1] += 1

    with open(path, newline="", encoding="utf-8") as f:
        rdr = csv.reader(f)
        next(rdr)
        for row in rdr:
            code, bdate_s, tno, lno, closed, item, qty_s, price_s, disc_s, state, _mode = row
            bd = parse_date(bdate_s)
            key = (code, bd)
            if key != cur_key:
                flush()
                cur_key = key
                day_lines = {}
            lk = (tno, lno)
            prev = day_lines.get(lk)
            if prev is None or closed > prev[0]:   # dedup-keep-latest
                day_lines[lk] = (closed, item, int(qty_s), parse_cents(price_s),
                                 parse_cents(disc_s), state)
    flush()
    return daily_net, attach, comp_month


def weekly(d: dict) -> dict:
    out: dict[tuple, int] = {}
    for (loc, day), v in d.items():
        iy, iw, _ = day.isocalendar()
        out[(loc, iy, iw)] = out.get((loc, iy, iw), 0) + v
    return out


def scan_small(path: str, bridge: dict, date_col: int, code_col: int, val_col: int):
    out: dict[tuple, int] = {}
    with open(path, newline="", encoding="utf-8") as f:
        rdr = csv.reader(f)
        next(rdr)
        for row in rdr:
            loc = bridge[row[code_col]]
            d = parse_date(row[date_col])
            out[(loc, d)] = out.get((loc, d), 0) + parse_cents(row[val_col])
    return out


def longest_streak(flags: list) -> int:
    best = run = 0
    for f in flags:
        run = run + 1 if f else 0
        best = max(best, run)
    return best


def main() -> int:
    out_dir, seeds = config.OUT_DIR, config.SEEDS_DIR
    bridge, alias, na_ids, loc_rows = load_seeds(seeds)

    print("scanning tickets...")
    daily_net, attach, comp_month = scan_tickets(
        f"{out_dir}/pos_ticket_lines.csv", bridge, alias, na_ids)
    print("scanning labor and invoices...")
    daily_labor = scan_small(f"{out_dir}/labor_daily.csv", bridge, 0, 1, 4)
    daily_cogs = scan_small(f"{out_dir}/ap_invoice_lines.csv", bridge, 4, 2, 10)

    wnet, wlab, wcog = weekly(daily_net), weekly(daily_labor), weekly(daily_cogs)
    locs = sorted({k[0] for k in daily_net})

    failures = []

    # ---- Band A: Financial District trailing-12 prime-cost miss
    def window_sum(d, loc, a, b):
        return sum(v for (l, day), v in d.items() if l == loc and a <= day <= b)

    net12 = window_sum(daily_net, FIDI, T12_FROM, T12_TO)
    prime12 = (window_sum(daily_labor, FIDI, T12_FROM, T12_TO) +
               window_sum(daily_cogs, FIDI, T12_FROM, T12_TO)) / net12 * 100
    miss = prime12 - config.PRIME_TARGET
    lo, hi = config.BAND_FIDI_T12_MISS
    ok = lo <= miss <= hi
    print(f"A. FiDi T12 prime {prime12:.2f}% -> miss {miss:+.2f} pts (band {lo}..{hi}) "
          f"{'OK' if ok else 'FAIL'}")
    if not ok:
        failures.append("A")

    # ---- Band B: rolling-4-week prime > threshold streaks
    streaks = {}
    for loc in locs:
        weeks = sorted({k[1:] for k in wnet if k[0] == loc})
        flags = []
        for i in range(3, len(weeks)):
            w4 = weeks[i - 3:i + 1]
            n = sum(wnet.get((loc, *w), 0) for w in w4)
            if n <= 0 or any(wnet.get((loc, *w), 0) <= 0 for w in w4):
                flags.append(False)
                continue
            c = sum(wcog.get((loc, *w), 0) for w in w4)
            l = sum(wlab.get((loc, *w), 0) for w in w4)
            flags.append((c + l) / n * 100 > config.STREAK_THRESHOLD)
        streaks[loc] = longest_streak(flags)
    runner_up = max(v for k, v in streaks.items() if k != FIDI)
    ok = (streaks[FIDI] >= config.BAND_STREAK_MIN_WEEKS and
          streaks[FIDI] >= config.BAND_STREAK_RUNNERUP_MULT * runner_up)
    print(f"B. streak weeks {streaks} -> FiDi {streaks[FIDI]} vs runner-up {runner_up} "
          f"(need >={config.BAND_STREAK_MIN_WEEKS} and >={config.BAND_STREAK_RUNNERUP_MULT}x) "
          f"{'OK' if ok else 'FAIL'}")
    if not ok:
        failures.append("B")

    # ---- Band C: naive vs comp H1-2026 YoY spread
    h1_26 = (date(2026, 1, 1), date(2026, 6, 30))
    h1_25 = (date(2025, 1, 1), date(2025, 6, 30))
    comp_set = [l for l in locs if l not in (3, 9)]   # converted + <13 months excluded
    naive = (sum(window_sum(daily_net, l, *h1_26) for l in locs) /
             sum(window_sum(daily_net, l, *h1_25) for l in locs) - 1) * 100
    comp = (sum(window_sum(daily_net, l, *h1_26) for l in comp_set) /
            sum(window_sum(daily_net, l, *h1_25) for l in comp_set) - 1) * 100
    spread = naive - comp
    ok = spread >= config.BAND_NAIVE_VS_COMP_MIN
    print(f"C. H1-26 YoY naive {naive:+.2f}% vs comp {comp:+.2f}% -> spread {spread:.2f} pts "
          f"(need >={config.BAND_NAIVE_VS_COMP_MIN}) {'OK' if ok else 'FAIL'}")
    if not ok:
        failures.append("C")

    # ---- Band D: NA-beverage attach gap (T12 window)
    g_t, g_n = sum(a[0] for a in attach.values()), sum(a[1] for a in attach.values())
    group_attach = g_n / g_t * 100
    fidi_attach = attach[FIDI][1] / attach[FIDI][0] * 100
    gap = group_attach - fidi_attach
    ok = gap >= config.BAND_ATTACH_GAP_MIN
    print(f"D. NA attach group {group_attach:.1f}% vs FiDi {fidi_attach:.1f}% -> gap {gap:.1f} pts "
          f"(need >={config.BAND_ATTACH_GAP_MIN}) {'OK' if ok else 'FAIL'}")
    if not ok:
        failures.append("D")

    # ---- informational
    for yr in (2024, 2025):
        print(f"\nrealized annualized net by location ({yr}):")
        for loc in locs:
            n = window_sum(daily_net, loc, date(yr, 1, 1), date(yr, 12, 31))
            days = sum(1 for (l, d) in daily_net if l == loc and d.year == yr)
            if days:
                print(f"  loc {loc}: ${n / days * 365 / 100 / 1e6:.2f}M over {days} open days")
    grp_net = sum(v for k, v in daily_net.items())
    grp_prime = (sum(daily_labor.values()) + sum(daily_cogs.values())) / grp_net * 100
    print(f"group prime cost, full window: {grp_prime:.2f}%")
    hot = sorted(((c / n * 100, l, y, m) for (l, y, m), (c, n) in comp_month.items() if n > 0),
                 reverse=True)[:4]
    print("highest comp-rate months:", [(f"loc{l} {y}-{m:02d} {r:.1f}%") for r, l, y, m in hot])

    if failures:
        print(f"\nCALIBRATION FAIL: bands {failures}")
        return 1
    print("\nCALIBRATION OK: all bands inside tolerance")
    return 0


if __name__ == "__main__":
    sys.exit(main())
