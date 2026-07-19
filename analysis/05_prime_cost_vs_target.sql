-- 05 | Prime cost vs monthly budget target
--
-- Business question: which locations missed their monthly prime-cost target
-- by more than 2 points, and when?
-- Prime cost = (purchases + labor) / net sales. Purchases are a COGS proxy
-- (no inventory counts): monthly granularity is the floor, and the streak
-- analysis in 08 uses rolling 4-week windows for the same reason.
-- Pattern: LEFT JOIN + COALESCE (budget rows start at each location's first
-- full open month, so missing budget months are real), aggregate + HAVING.

WITH monthly AS (
    SELECT
        f.location_id,
        date_trunc('month', f.business_date)::date AS month_start,
        sum(f.net_amount)                          AS net_sales
    FROM marts.fact_ticket_line f
    GROUP BY 1, 2
),
cogs AS (
    SELECT
        location_id,
        date_trunc('month', invoice_date)::date AS month_start,
        sum(ext_cost)                           AS purchases
    FROM marts.fact_invoice_line
    GROUP BY 1, 2
),
labor AS (
    SELECT
        location_id,
        date_trunc('month', business_date)::date AS month_start,
        sum(wages)                               AS labor_cost
    FROM marts.fact_labor_day
    GROUP BY 1, 2
)
SELECT
    l.location_code,
    to_char(m.month_start, 'YYYY-MM')                                  AS month,
    round(100.0 * (COALESCE(c.purchases, 0) + COALESCE(w.labor_cost, 0))
          / m.net_sales, 2)                                            AS prime_pct,
    round(100.0 * (b.cogs_budget + b.labor_budget)
          / nullif(b.net_sales_budget, 0), 2)                          AS target_pct,
    round(100.0 * (COALESCE(c.purchases, 0) + COALESCE(w.labor_cost, 0)) / m.net_sales
          - 100.0 * (b.cogs_budget + b.labor_budget) / nullif(b.net_sales_budget, 0), 2)
                                                                       AS miss_pts,
    (b.month_start IS NULL)                                            AS no_budget_row
FROM monthly m
JOIN marts.dim_location l USING (location_id)
LEFT JOIN cogs c USING (location_id, month_start)
LEFT JOIN labor w USING (location_id, month_start)
LEFT JOIN marts.fact_budget_month b USING (location_id, month_start)
WHERE m.net_sales > 0
  AND (100.0 * (COALESCE(c.purchases, 0) + COALESCE(w.labor_cost, 0)) / m.net_sales)
      - COALESCE(100.0 * (b.cogs_budget + b.labor_budget) / nullif(b.net_sales_budget, 0), 60.0)
      > 2.0
ORDER BY miss_pts DESC;
