-- marts.fact_labor_day: location x business date x role. Payroll uses
-- canonical location codes (it never re-keyed with the POS), and role casing
-- variants collapse under normalization, so the grain is enforced by summing
-- to it. Wages are blended, fully loaded employer cost.

DROP TABLE IF EXISTS marts.fact_labor_day CASCADE;
CREATE TABLE marts.fact_labor_day (
    location_id   smallint NOT NULL REFERENCES marts.dim_location,
    business_date date NOT NULL REFERENCES marts.dim_date,
    role          text NOT NULL CHECK (role IN
        ('Manager', 'Line Cook', 'Prep Cook', 'Server', 'Busser',
         'Bartender', 'Counter', 'Dishwasher')),
    hours         numeric(6,2) NOT NULL CHECK (hours >= 0),
    wages         numeric(9,2) NOT NULL CHECK (wages >= 0),
    PRIMARY KEY (location_id, business_date, role)
);

INSERT INTO marts.fact_labor_day
SELECT
    b.location_id::smallint,
    l.business_date,
    l.role,
    sum(l.hours),
    sum(l.wages)
FROM staging.stg_labor__daily l
JOIN raw.ref_location_bridge b ON b.location_code = l.location_code
GROUP BY 1, 2, 3;

CREATE INDEX idx_fld_business_date ON marts.fact_labor_day (business_date);
ANALYZE marts.fact_labor_day;
