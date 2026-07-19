"""All generation parameters in one place.

Hard rule (project CLAUDE-level): the generator is deterministic. Fixed SEED,
no wall clock anywhere (START/END are constants), a single numpy PCG64 stream
consumed in a fixed order, and every messiness item below is a named,
parameterized injection, not noise. Changing anything here legitimately changes
the byte stream: bump DATASET_VERSION and regenerate the manifest in the same
commit.
"""

from dataclasses import dataclass
from datetime import date, datetime

SEED = 20260719
DATASET_VERSION = "1.0.0"

START_DATE = date(2024, 1, 1)
END_DATE = date(2026, 6, 30)          # last complete month; never derived from a clock

# 2025-06-15 menu price round: +3% rounded to nearest 50c, beef flagships held.
PRICE_ROUND_DATE = date(2025, 6, 15)

# America/New_York DST transition instants (local standard time, historical facts,
# hardcoded so byte-identity never depends on a tzdata package). (utc_offset_hours)
DST_TRANSITIONS = (
    (datetime(2024, 3, 10, 2, 0), -4),
    (datetime(2024, 11, 3, 2, 0), -5),
    (datetime(2025, 3, 9, 2, 0), -4),
    (datetime(2025, 11, 2, 2, 0), -5),
    (datetime(2026, 3, 8, 2, 0), -4),
    (datetime(2026, 11, 1, 2, 0), -5),
)
BASE_UTC_OFFSET = -5  # before first transition above

# Full-day closures (tickets = 0).
CLOSED_HOLIDAYS = ("Thanksgiving", "Christmas Day")

# COGS: purchases-as-proxy waste/yield factor over theoretical item cost.
WASTE_FACTOR = 1.075
# Packaging cost per to-go/delivery ticket (cents), by service format.
PACKAGING_PER_TOGO_TICKET = {"full_service": 55, "counter_service": 85}

OUT_DIR = "data/generated"
SEEDS_DIR = "seeds"
SAMPLES_ROWS = 500

# Fixed output file lists: nothing in the generator ever walks a directory.
FACT_FILES = ("pos_ticket_lines.csv", "ap_invoice_lines.csv", "labor_daily.csv", "gl_daily_sales.csv")
SEED_FILES = ("pos_locations.csv", "pos_menu_items.csv", "ap_vendors.csv", "plan_budget.csv",
              "ref_calendar.csv", "ref_dayparts.csv", "ref_item_aliases.csv", "ref_location_bridge.csv")

# ------------------------------------------------------------------ messiness
# One frozen block per catalog item; docs/DATASET.md documents each as a
# cleaning step. Rates are fractions of eligible rows unless noted.


@dataclass(frozen=True)
class NameDrift:                      # item 1
    rate: float = 0.055               # share of eligible dish lines using a variant
    gcx_rate: float = 0.14            # CW-GCX re-keyed POS, first months
    gcx_hot_months: int = 3


@dataclass(frozen=True)
class GlVarianceWindow:               # item 2
    location_id: int
    date_from: date
    date_to: date
    mode: str                         # deposit_shift | missing_day | rounding
GL_WINDOWS = (
    GlVarianceWindow(2, date(2024, 6, 10), date(2024, 6, 23), "deposit_shift"),
    GlVarianceWindow(5, date(2024, 10, 7), date(2024, 10, 13), "deposit_shift"),
    GlVarianceWindow(8, date(2025, 2, 3), date(2025, 2, 9), "missing_day"),
    GlVarianceWindow(4, date(2026, 3, 16), date(2026, 3, 29), "rounding"),
)


@dataclass(frozen=True)
class DuplicateWindow:                # item 3: re-fired tickets. Duplicates share
    location_id: int | None           # the full business key (incl. business_date)
    date_from: date                   # and differ only in closed_at (+45..180s).
    date_to: date
    rate: float
DUP_WINDOWS = (
    DuplicateWindow(None, date(2024, 5, 6), date(2024, 5, 12), 0.004),   # POS patch week, all stores
    DuplicateWindow(6, date(2025, 11, 1), date(2025, 11, 30), 0.012),    # Williamsburg November
)


@dataclass(frozen=True)
class LatePosting:                    # item 4
    ticket_rate: float = 0.006        # month-end tickets: closed_at posts 1-2 days late
    ticket_window_days: int = 3       # last N days of each month are eligible
    invoice_rate: float = 0.03        # invoices: posted_date = invoice_date + 14..35d
    invoice_quarter_end_only: bool = True


@dataclass(frozen=True)
class LineStates:                     # item 5 (business reality, cleaned not "fixed")
    void_rate: float = 0.011
    comp_rate: float = 0.016
    refund_rate: float = 0.004


@dataclass(frozen=True)
class CompSpike:                      # feeds query 01's HAVING exception list
    location_id: int
    year: int
    month: int
    comp_rate: float
COMP_SPIKES = (
    CompSpike(1, 2025, 12, 0.038),    # West Village holiday comps
    CompSpike(6, 2025, 11, 0.034),    # Williamsburg, overlaps the dup window on purpose
)


@dataclass(frozen=True)
class NullCosts:                      # item 6 (invoice side; menu side is static)
    vendor_key: str = "produce"
    date_from: date = date(2024, 4, 1)
    date_to: date = date(2024, 6, 30)
    rate: float = 0.02                # unit_cost blank, ext_cost kept


@dataclass(frozen=True)
class DateFormatWindow:               # item 7
    location_id: int
    date_from: date
    date_to: date
    fmt: str                          # strftime for business_date
DATE_FORMAT_WINDOWS = (
    DateFormatWindow(2, date(2024, 1, 1), date(2024, 9, 30), "%m/%d/%Y"),
    DateFormatWindow(7, date(2024, 1, 1), date(2024, 12, 31), "%Y/%m/%d"),
)


@dataclass(frozen=True)
class UtcExportWindow:                # item 7b: closed_at rendered as UTC ISO-8601 Z
    location_id: int = 6
    date_from: date = date(2025, 3, 1)
    date_to: date = date(2025, 5, 31)


@dataclass(frozen=True)
class CategoricalTypos:               # item 8 (menu side is static in content.py)
    uom_rate: float = 0.07            # CS->case/Case, LB->lb, EA->ea
    role_rate: float = 0.04           # LINE COOK / line cook / 'Server '


@dataclass(frozen=True)
class Outlier:                        # item 9: explicit planted rows
    location_id: int
    day: date
    field: str                        # unit_price | qty | discount
    value: int                        # cents or count
OUTLIERS = (
    Outlier(1, date(2024, 7, 9), "unit_price", 999900),    # the mis-keyed $9,999 check
    Outlier(5, date(2025, 5, 21), "qty", 99),
    Outlier(7, date(2024, 11, 30), "unit_price", 1),
    Outlier(2, date(2026, 2, 14), "discount", 25000),      # discount larger than the line
    Outlier(8, date(2025, 8, 8), "unit_price", 19900),
    Outlier(6, date(2024, 3, 3), "qty", -3),               # negative qty on a sale line
)

# item 10 (location re-code) is structural: see content.LOCATIONS Grand Central eras.

MESS_NAME_DRIFT = NameDrift()
MESS_LATE = LatePosting()
MESS_STATES = LineStates()
MESS_NULL_COSTS = NullCosts()
MESS_UTC_WINDOW = UtcExportWindow()
MESS_TYPOS = CategoricalTypos()

# ------------------------------------------------------------------ scenarios
# Planted findings are parameter adjustments applied BEFORE drawing, never
# pasted rows. Values are calibration levers; the memo transcribes only
# measured query output, never these constants.


@dataclass(frozen=True)
class LaborCostCreep:                 # decision-memo leg 1 (Financial District)
    location_id: int = 5
    start: date = date(2025, 1, 4)    # first weekend after the group template rollout
    weekend_extra_hours: dict = None  # role -> deci-hours added per weekend day
    overlap_start: date = date(2025, 4, 1)
    overlap_extra: dict = None        # role -> deci-hours added per day, all days

    def __post_init__(self):
        object.__setattr__(self, "weekend_extra_hours",
                           {"server": 200, "busser": 110, "line_cook": 105})
        object.__setattr__(self, "overlap_extra", {"line_cook": 25})


@dataclass(frozen=True)
class VendorPriceIncrease:            # decision-memo leg 2 (beef steps)
    steps: tuple = ((date(2025, 3, 1), 1.065), (date(2025, 9, 1), 1.08))

    def factor(self, d: date) -> float:
        f = 1.0
        for start, mult in self.steps:
            if d >= start:
                f *= mult
        return f


@dataclass(frozen=True)
class AstoriaRamp:                    # opening honeymoon -> dip -> ramp to run rate
    honeymoon_weeks: int = 6
    honeymoon_mult: float = 1.25
    dip_weeks: int = 6
    dip_mult: float = 0.85
    ramp_to_one_weeks: int = 26


LABOR_CREEP = LaborCostCreep()
BEEF_STEPS = VendorPriceIncrease()
AST_RAMP = AstoriaRamp()

# ------------------------------------------------------------------ calibration
# Tolerance bands, not point targets (rule 5: public numbers are measured, not
# specified). generator/calibrate.py fails outside these bands.
BAND_FIDI_T12_MISS = (4.0, 4.6)       # pts over the 60.0% prime-cost target, 2025-07..2026-06
BAND_STREAK_MIN_WEEKS = 30            # rolling 4-week prime > 62%, consecutive ISO weeks
BAND_STREAK_RUNNERUP_MULT = 2.5
BAND_NAIVE_VS_COMP_MIN = 3.0          # pts, H1-2026 YoY
BAND_ATTACH_GAP_MIN = 8.0             # pts, group NA attach minus Financial District
PRIME_TARGET = 60.0
STREAK_THRESHOLD = 62.0
