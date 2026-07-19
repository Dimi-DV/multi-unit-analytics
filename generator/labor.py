"""Daily labor at location x business date x role grain.

Payroll is a finance-side system: canonical location codes throughout (N-series
contract: payroll never re-keys with a POS reinstall). Role sets depend on
service format: counter-service stores carry no servers, bussers, or bartenders.

The Financial District scenario is additive scheduled hours (a weekend template
that was never rescaled), not a percentage fudge: weekday labor stays on plan
while weekend labor detaches from demand, which is exactly the diagnostic shape
the analysis queries need to find.
"""

from datetime import date, timedelta

import numpy as np

from . import config, content, writers

LABOR_HEADER = ["business_date", "location_code", "role", "hours", "wages"]

ROLE_DISPLAY = {"manager": "Manager", "line_cook": "Line Cook", "prep_cook": "Prep Cook",
                "server": "Server", "busser": "Busser", "bartender": "Bartender",
                "counter": "Counter", "dishwasher": "Dishwasher"}


def _rate(role: str, d: date) -> int:
    r = content.ROLE_RATE[role]
    if d.year >= 2026:
        r = int(round(r * content.ROLE_RATE_2026_MULT))
    return r


def _era_for(loc, d):
    for era in loc.eras:
        if era.valid_from <= d and (era.valid_to is None or d <= era.valid_to):
            return era
    return loc.eras[0]


def generate(rng: np.random.Generator, writer: writers.TableWriter, aggregates: dict) -> None:
    daily_net = aggregates["daily_net"]
    creep = config.LABOR_CREEP
    typos = config.MESS_TYPOS

    for loc in content.LOCATIONS:
        canon = loc.eras[0].code
        d = max(config.START_DATE, loc.open_date)
        while d <= config.END_DATE:
            net = daily_net.get((loc.location_id, d), 0)
            if net <= 0:
                d += timedelta(days=1)
                continue
            era = _era_for(loc, d)
            pct = era.labor_pct
            if loc.location_id == 9 and (d - loc.open_date).days < 56:
                pct *= 1.15   # opening crew inefficiency, first 8 weeks
            noise = 1.0 + (rng.random() - 0.5) * 0.04
            labor_cents = int(net * pct * noise)

            if era.service_format == "counter_service":
                roles, shares = content.ROLES_COUNTER, content.ROLE_SHARE_COUNTER
            else:
                roles, shares = content.ROLES_FULL, content.ROLE_SHARE_FULL

            extra: dict[str, int] = {}
            if loc.location_id == creep.location_id and d >= creep.start and d.weekday() >= 5:
                extra = dict(creep.weekend_extra_hours)
            if loc.location_id == creep.location_id and d >= creep.overlap_start:
                for role, dh in creep.overlap_extra.items():
                    extra[role] = extra.get(role, 0) + dh

            role_rolls = rng.random(len(roles))
            for i, role in enumerate(roles):
                rate = _rate(role, d)
                hours_deci = int(round(labor_cents * shares[role] * 10 / rate))
                hours_deci += extra.get(role, 0) * 1  # deci-hours
                if hours_deci <= 0:
                    continue
                wages = (hours_deci * rate + 5) // 10
                name = ROLE_DISPLAY[role]
                if role_rolls[i] < typos.role_rate:
                    pick = int(role_rolls[i] / typos.role_rate * 3)
                    name = (name.upper(), name.lower(), name + " ")[pick]
                writer.write([d.isoformat(), canon, name,
                              writers.tenths(hours_deci), writers.money(wages)])
            d += timedelta(days=1)
