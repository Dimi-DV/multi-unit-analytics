"""Calendar content: holidays, dayparts, school breaks, city events.

Everything is computed from pure date arithmetic (no wall clock). Movable
feasts are golden-asserted against hand-verified dates so an algorithm bug
cannot silently ship a wrong calendar seed.
"""

from datetime import date, timedelta

from . import config

DAYPARTS = [
    ("breakfast", "07:00", "10:59"),
    ("lunch", "11:00", "14:59"),
    ("afternoon", "15:00", "16:59"),
    ("dinner", "17:00", "21:59"),
    ("late_night", "22:00", "01:59"),   # wraps midnight; posts to prior service date
]


def easter(year: int) -> date:
    # Anonymous Gregorian algorithm.
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month, day = divmod(h + l - 7 * m + 114, 31)
    return date(year, month, day + 1)


def nth_weekday(year: int, month: int, weekday: int, n: int) -> date:
    """n-th (1-based) weekday (Mon=0) of a month."""
    d = date(year, month, 1)
    offset = (weekday - d.weekday()) % 7
    return d + timedelta(days=offset + 7 * (n - 1))


def last_weekday(year: int, month: int, weekday: int) -> date:
    d = date(year, month + 1, 1) - timedelta(days=1) if month < 12 else date(year, 12, 31)
    return d - timedelta(days=(d.weekday() - weekday) % 7)


def holidays_for_year(year: int) -> dict[date, tuple[str, str]]:
    e = easter(year)
    tg = nth_weekday(year, 11, 3, 4)  # 4th Thursday of November
    h = {
        date(year, 1, 1): ("New Year's Day", "federal"),
        nth_weekday(year, 1, 0, 3): ("MLK Day", "federal"),
        nth_weekday(year, 2, 0, 3): ("Washington's Birthday", "federal"),
        last_weekday(year, 5, 0): ("Memorial Day", "federal"),
        date(year, 6, 19): ("Juneteenth", "federal"),
        date(year, 7, 4): ("Independence Day", "federal"),
        nth_weekday(year, 9, 0, 1): ("Labor Day", "federal"),
        nth_weekday(year, 10, 0, 2): ("Columbus Day", "federal"),
        date(year, 11, 11): ("Veterans Day", "federal"),
        tg: ("Thanksgiving", "federal"),
        date(year, 12, 25): ("Christmas Day", "federal"),
        date(year, 2, 14): ("Valentine's Day", "observance"),
        e: ("Easter Sunday", "observance"),
        nth_weekday(year, 5, 6, 2): ("Mother's Day", "observance"),
        nth_weekday(year, 6, 6, 3): ("Father's Day", "observance"),
        date(year, 10, 31): ("Halloween", "observance"),
        tg - timedelta(days=1): ("Thanksgiving Eve", "observance"),
        date(year, 12, 31): ("New Year's Eve", "observance"),
        nth_weekday(year, 2, 6, 2): ("Super Bowl Sunday", "observance"),
        nth_weekday(year, 11, 6, 1): ("Marathon Sunday", "city_event"),
    }
    return h


def _golden_asserts() -> None:
    assert easter(2024) == date(2024, 3, 31)
    assert easter(2025) == date(2025, 4, 20)
    assert easter(2026) == date(2026, 4, 5)
    assert nth_weekday(2024, 11, 3, 4) == date(2024, 11, 28)   # Thanksgiving 2024
    assert nth_weekday(2025, 11, 3, 4) == date(2025, 11, 27)
    assert nth_weekday(2024, 5, 6, 2) == date(2024, 5, 12)     # Mother's Day 2024
    assert nth_weekday(2025, 5, 6, 2) == date(2025, 5, 11)
    assert nth_weekday(2026, 5, 6, 2) == date(2026, 5, 10)
    assert nth_weekday(2025, 2, 6, 2) == date(2025, 2, 9)      # Super Bowl 2025
    assert nth_weekday(2025, 11, 6, 1) == date(2025, 11, 2)    # Marathon 2025
    assert last_weekday(2025, 5, 0) == date(2025, 5, 26)       # Memorial Day 2025


_golden_asserts()


def school_break_windows(year: int) -> list[tuple[date, date]]:
    """Approximate NYC public-school recesses (authored approximation, documented)."""
    pres = nth_weekday(year, 2, 0, 3)
    windows = [(pres, pres + timedelta(days=4))]                      # midwinter recess
    spring = {2024: (date(2024, 4, 22), date(2024, 4, 30)),
              2025: (date(2025, 4, 14), date(2025, 4, 18)),
              2026: (date(2026, 3, 30), date(2026, 4, 3))}
    windows.append(spring[year])
    windows.append((date(year, 6, 27), date(year, 9, 5)))             # summer
    return windows


def dining_week_windows(year: int) -> list[tuple[date, date]]:
    """Invented citywide dining-week promo windows (no trademarked program names)."""
    w = [(date(year, 1, 16), date(year, 1, 31))]
    if date(year, 7, 22) <= config.END_DATE:
        w.append((date(year, 7, 22), date(year, 8, 8)))
    return w


def build_calendar() -> dict[date, dict]:
    """One record per day in the window, in date order."""
    days: dict[date, dict] = {}
    holidays: dict[date, tuple[str, str]] = {}
    school: list[tuple[date, date]] = []
    dining: list[tuple[date, date]] = []
    for y in (2024, 2025, 2026):
        holidays.update(holidays_for_year(y))
        school.extend(school_break_windows(y))
        dining.extend(dining_week_windows(y))

    d = config.START_DATE
    while d <= config.END_DATE:
        hol = holidays.get(d)
        days[d] = {
            "holiday_name": hol[0] if hol else "",
            "holiday_type": hol[1] if hol else "",
            "is_school_break": any(a <= d <= b for a, b in school),
            "is_dining_week": any(a <= d <= b for a, b in dining),
            "is_marathon_sunday": bool(hol and hol[0] == "Marathon Sunday"),
            "is_weekend": d.weekday() >= 5,
        }
        d += timedelta(days=1)
    return days


# Demand multipliers by holiday name; (default, per-location overrides by id).
HOLIDAY_DEMAND = {
    "Thanksgiving": (0.0, {}),
    "Christmas Day": (0.0, {}),
    "New Year's Day": (0.75, {}),
    "New Year's Eve": (1.30, {}),
    "Valentine's Day": (1.25, {}),
    "Easter Sunday": (1.20, {2: 1.35, 7: 1.35}),
    "Mother's Day": (1.15, {1: 1.45, 2: 1.50, 7: 1.50, 9: 1.45}),
    "Father's Day": (1.20, {}),
    "Super Bowl Sunday": (0.70, {}),
    "Marathon Sunday": (1.00, {1: 1.15, 2: 1.60}),
    "Independence Day": (0.70, {}),
    "Memorial Day": (0.85, {}),
    "Labor Day": (0.85, {}),
    "Halloween": (1.10, {}),
    "Thanksgiving Eve": (1.20, {}),
    "MLK Day": (1.00, {3: 0.80, 5: 0.80}),
    "Washington's Birthday": (1.00, {3: 0.80, 5: 0.80}),
    "Juneteenth": (1.00, {3: 0.85, 5: 0.85}),
    "Columbus Day": (1.00, {3: 0.90, 5: 0.90}),
    "Veterans Day": (1.00, {3: 0.90, 5: 0.90}),
}
