-- 12 | Decision memo assembly: the Financial District prime-cost bridge
--
-- Business question: decompose the Financial District's trailing-12
-- (2025-07 .. 2026-06) prime-cost miss vs the 60.0% target into labor and
-- COGS legs, split the labor leg into weekend vs weekday to isolate the
-- unrescaled weekend template, and annualize the dollars.
-- Every number in docs/decision-memo.md and the README executive summary is
-- transcribed from THIS query's output; none of it comes from generator
-- parameters.
-- Pattern: multi-CTE composition over the same building blocks as 04/05/08/10.

WITH fidi AS (
    SELECT location_id FROM marts.dim_location WHERE location_code = 'CW-FD'
),
windows AS (
    SELECT 'baseline_fy2024' AS era, date '2024-01-01' AS d1, date '2024-12-31' AS d2
    UNION ALL
    SELECT 'trailing_12', date '2025-07-01', date '2026-06-30'
),
net AS (
    SELECT w.era,
           sum(f.net_amount) AS net_sales,
           sum(f.net_amount) FILTER (WHERE extract(isodow FROM f.business_date) IN (6, 7)) AS net_weekend
    FROM marts.fact_ticket_line f
    JOIN fidi USING (location_id)
    JOIN windows w ON f.business_date BETWEEN w.d1 AND w.d2
    GROUP BY w.era
),
labor AS (
    SELECT w.era,
           sum(d.wages) AS labor_cost,
           sum(d.wages) FILTER (WHERE extract(isodow FROM d.business_date) IN (6, 7)) AS labor_weekend
    FROM marts.fact_labor_day d
    JOIN fidi USING (location_id)
    JOIN windows w ON d.business_date BETWEEN w.d1 AND w.d2
    GROUP BY w.era
),
cogs AS (
    SELECT w.era, sum(i.ext_cost) AS purchases
    FROM marts.fact_invoice_line i
    JOIN fidi USING (location_id)
    JOIN windows w ON i.invoice_date BETWEEN w.d1 AND w.d2
    GROUP BY w.era
),
pct AS (
    SELECT
        n.era,
        n.net_sales,
        100.0 * l.labor_cost / n.net_sales                    AS labor_pct,
        100.0 * c.purchases / n.net_sales                     AS cogs_pct,
        100.0 * (l.labor_cost + c.purchases) / n.net_sales    AS prime_pct,
        100.0 * l.labor_weekend / nullif(n.net_weekend, 0)    AS weekend_labor_pct,
        100.0 * (l.labor_cost - l.labor_weekend)
              / nullif(n.net_sales - n.net_weekend, 0)        AS weekday_labor_pct
    FROM net n
    JOIN labor l USING (era)
    JOIN cogs c USING (era)
)
SELECT
    'prime cost, % of net sales' AS line,
    round(b.prime_pct, 2)  AS baseline_fy2024,
    round(t.prime_pct, 2)  AS trailing_12,
    round(t.prime_pct - b.prime_pct, 2) AS delta_pts
FROM pct b, pct t
WHERE b.era = 'baseline_fy2024' AND t.era = 'trailing_12'
UNION ALL
SELECT 'labor leg', round(b.labor_pct, 2), round(t.labor_pct, 2),
       round(t.labor_pct - b.labor_pct, 2)
FROM pct b, pct t WHERE b.era = 'baseline_fy2024' AND t.era = 'trailing_12'
UNION ALL
SELECT '  of which weekend labor %', round(b.weekend_labor_pct, 2),
       round(t.weekend_labor_pct, 2), round(t.weekend_labor_pct - b.weekend_labor_pct, 2)
FROM pct b, pct t WHERE b.era = 'baseline_fy2024' AND t.era = 'trailing_12'
UNION ALL
SELECT '  of which weekday labor %', round(b.weekday_labor_pct, 2),
       round(t.weekday_labor_pct, 2), round(t.weekday_labor_pct - b.weekday_labor_pct, 2)
FROM pct b, pct t WHERE b.era = 'baseline_fy2024' AND t.era = 'trailing_12'
UNION ALL
SELECT 'COGS leg (purchases)', round(b.cogs_pct, 2), round(t.cogs_pct, 2),
       round(t.cogs_pct - b.cogs_pct, 2)
FROM pct b, pct t WHERE b.era = 'baseline_fy2024' AND t.era = 'trailing_12';

-- The headline: miss vs the 60.0 target and annualized dollars
WITH fidi AS (
    SELECT location_id FROM marts.dim_location WHERE location_code = 'CW-FD'
),
t12 AS (
    SELECT
        (SELECT sum(net_amount) FROM marts.fact_ticket_line f JOIN fidi USING (location_id)
         WHERE f.business_date BETWEEN date '2025-07-01' AND date '2026-06-30') AS net_sales,
        (SELECT sum(wages) FROM marts.fact_labor_day d JOIN fidi USING (location_id)
         WHERE d.business_date BETWEEN date '2025-07-01' AND date '2026-06-30') AS labor_cost,
        (SELECT sum(ext_cost) FROM marts.fact_invoice_line i JOIN fidi USING (location_id)
         WHERE i.invoice_date BETWEEN date '2025-07-01' AND date '2026-06-30')  AS purchases
)
SELECT
    round(100.0 * (labor_cost + purchases) / net_sales, 2)          AS prime_pct_t12,
    round(100.0 * (labor_cost + purchases) / net_sales - 60.0, 2)   AS miss_vs_target_pts,
    round(net_sales, 0)                                             AS net_sales_t12,
    round((100.0 * (labor_cost + purchases) / net_sales - 60.0)
          / 100.0 * net_sales, 0)                                   AS annualized_excess_cost
FROM t12;
