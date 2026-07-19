-- staging.stg_plan__budget: types over raw.plan_budget. Budget rows start at
-- each location's first full open month; the converted store is re-planned
-- from 2025-07 under its canonical code.

CREATE OR REPLACE VIEW staging.stg_plan__budget AS
SELECT
    month_start::date               AS month_start,
    location_code,
    net_sales_budget::numeric(12,2) AS net_sales_budget,
    cogs_budget::numeric(12,2)      AS cogs_budget,
    labor_budget::numeric(12,2)     AS labor_budget
FROM raw.plan_budget;
