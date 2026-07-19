-- marts.fact_budget_month: location x month plan. Rows begin at each
-- location's first full open month, so LEFT JOIN + COALESCE handling in
-- analysis is a real requirement, not a formality.

DROP TABLE IF EXISTS marts.fact_budget_month CASCADE;
CREATE TABLE marts.fact_budget_month (
    location_id      smallint NOT NULL REFERENCES marts.dim_location,
    month_start      date NOT NULL,
    net_sales_budget numeric(12,2) NOT NULL,
    cogs_budget      numeric(12,2) NOT NULL,
    labor_budget     numeric(12,2) NOT NULL,
    PRIMARY KEY (location_id, month_start),
    CHECK (extract(day FROM month_start) = 1)
);

INSERT INTO marts.fact_budget_month
SELECT
    b.location_id::smallint,
    p.month_start,
    p.net_sales_budget,
    p.cogs_budget,
    p.labor_budget
FROM staging.stg_plan__budget p
JOIN raw.ref_location_bridge b ON b.location_code = p.location_code;

ANALYZE marts.fact_budget_month;
