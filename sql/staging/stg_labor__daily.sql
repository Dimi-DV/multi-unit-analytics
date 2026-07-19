-- staging.stg_labor__daily: types plus role normalization (the payroll export
-- carries casing and whitespace variants of the same role).

CREATE OR REPLACE VIEW staging.stg_labor__daily AS
SELECT
    business_date::date     AS business_date,
    location_code,
    initcap(trim(role))     AS role,
    hours::numeric(6,2)     AS hours,
    wages::numeric(9,2)     AS wages
FROM raw.labor_daily;
