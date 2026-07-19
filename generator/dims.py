"""Committed seed CSVs: raw source dims and analyst-maintained reference maps.
No RNG anywhere in this module: seeds are pure authored content, so the
`git status --porcelain seeds/` CI check is a direct test of content stability.

Budget note: rows begin at each location's first full open month (Astoria
2025-10). Grand Central is re-planned at the 2025-07 conversion under its
canonical code; format-aware analysis resolves eras via ref_location_bridge
plus pos_locations dates.
"""

from datetime import date

from . import caldata, config, content, writers

AUV_CENTS = {  # annual plan by (location_id, era_index), ~2-4% above run rate
    (1, 0): 560_000_000, (2, 0): 395_000_000,
    (3, 0): 380_000_000, (3, 1): 245_000_000,
    (4, 0): 385_000_000, (5, 0): 310_000_000,
    (6, 0): 355_000_000, (7, 0): 315_000_000,
    (8, 0): 230_000_000, (9, 0): 330_000_000,
}
SEAS_SUM = sum(content.MONTH_SEASONALITY.values())   # normalizer, = 11.93
BUDGET_PCT = {"full_service": (0.275, 0.325), "counter_service": (0.290, 0.265)}


def _b(v: bool) -> str:
    return "true" if v else "false"


def write_all(seeds_dir: str) -> dict[str, int]:
    counts = {}

    rows = []
    for loc in content.LOCATIONS:
        for i, era in enumerate(loc.eras):
            open_d = loc.open_date if i == 0 else era.valid_from
            closed = era.valid_to.isoformat() if era.valid_to else ""
            rows.append([era.code, loc.name, loc.neighborhood, loc.borough,
                         era.service_format, era.volume_tier, str(era.seats),
                         open_d.isoformat(), closed])
    writers.write_seed(f"{seeds_dir}/pos_locations.csv",
                       ["location_code", "location_name", "neighborhood", "borough",
                        "service_format", "volume_tier", "seats", "open_date", "closed_date"], rows)
    counts["pos_locations"] = len(rows)

    rows = []
    for m in content.MENU:
        cat = content.MENU_CATEGORY_TYPOS.get(m.item_id, m.category)
        cost = "" if m.item_id in content.UNCOSTED_MENU_IDS else writers.money(m.price_cents * m.fc_bp // 10000)
        rows.append([str(m.item_id), m.name, cat, writers.money(m.price_cents), cost])
    writers.write_seed(f"{seeds_dir}/pos_menu_items.csv",
                       ["menu_item_id", "item_name", "category", "standard_price",
                        "theoretical_unit_cost"], rows)
    counts["pos_menu_items"] = len(rows)

    writers.write_seed(f"{seeds_dir}/ap_vendors.csv",
                       ["vendor_id", "vendor_name", "vendor_category"],
                       [list(r) for r in content.VENDOR_SEED_ROWS])
    counts["ap_vendors"] = len(content.VENDOR_SEED_ROWS)

    cal = caldata.build_calendar()
    rows = []
    for d, rec in cal.items():
        rows.append([d.isoformat(), str(d.year), str((d.month - 1) // 3 + 1), str(d.month),
                     d.strftime("%B"), str(d.isoweekday()), d.strftime("%A"),
                     _b(rec["is_weekend"]), _b(bool(rec["holiday_name"])),
                     rec["holiday_name"], rec["holiday_type"],
                     _b(rec["is_school_break"]), _b(rec["is_dining_week"]),
                     _b(rec["is_marathon_sunday"])])
    writers.write_seed(f"{seeds_dir}/ref_calendar.csv",
                       ["date_day", "year", "quarter", "month", "month_name", "day_of_week",
                        "day_name", "is_weekend", "is_holiday", "holiday_name", "holiday_type",
                        "is_school_break", "is_dining_week", "is_marathon_sunday"], rows)
    counts["ref_calendar"] = len(rows)

    writers.write_seed(f"{seeds_dir}/ref_dayparts.csv",
                       ["daypart", "start_time", "end_time"],
                       [[n, s, e] for n, s, e in caldata.DAYPARTS])
    counts["ref_dayparts"] = len(caldata.DAYPARTS)

    rows = [[m.name, str(m.item_id)] for m in content.MENU]
    for iid in sorted(content.DRIFT_VARIANTS):
        for v in content.DRIFT_VARIANTS[iid]:
            rows.append([v, str(iid)])
    for iid in sorted(content.DRIFT_VARIANTS_GCX):
        for v in content.DRIFT_VARIANTS_GCX[iid]:
            rows.append([v, str(iid)])
    writers.write_seed(f"{seeds_dir}/ref_item_aliases.csv", ["alias", "menu_item_id"], rows)
    counts["ref_item_aliases"] = len(rows)

    rows = []
    for loc in content.LOCATIONS:
        for era in loc.eras:
            rows.append([era.code, str(loc.location_id)])
    writers.write_seed(f"{seeds_dir}/ref_location_bridge.csv",
                       ["location_code", "location_id"], rows)
    counts["ref_location_bridge"] = len(rows)

    rows = []
    for loc in content.LOCATIONS:
        canon = loc.eras[0].code
        for i, era in enumerate(loc.eras):
            auv = AUV_CENTS[(loc.location_id, i)]
            cogs_p, labor_p = BUDGET_PCT[era.service_format]
            first = max(era.valid_from, loc.open_date, config.START_DATE)
            if first.day != 1:   # first full month only
                first = date(first.year + first.month // 12, first.month % 12 + 1, 1)
            m = first
            while m <= config.END_DATE and (era.valid_to is None or m <= era.valid_to):
                seas = content.MONTH_SEASONALITY[m.month]
                net_b = int(auv * seas / SEAS_SUM) // 10000 * 10000   # round to $100
                rows.append([m.isoformat(), canon, writers.money(net_b),
                             writers.money(int(net_b * cogs_p) // 10000 * 10000),
                             writers.money(int(net_b * labor_p) // 10000 * 10000)])
                m = date(m.year + m.month // 12, m.month % 12 + 1, 1)
    writers.write_seed(f"{seeds_dir}/plan_budget.csv",
                       ["month_start", "location_code", "net_sales_budget",
                        "cogs_budget", "labor_budget"], rows)
    counts["plan_budget"] = len(rows)
    return counts
