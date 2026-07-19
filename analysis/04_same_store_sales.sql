-- 04 | Same-store sales: comp growth vs naive growth (the headline query)
--
-- Business question: what is real comp growth vs naive growth?
-- Comp eligibility rule (documented in docs/DATASET.md): a location enters the
-- comp base for a month only if it was open 13 full calendar months as of BOTH
-- the current month and the prior-year month, and it leaves the base during a
-- format conversion and for 12 months after (comparing counter-service months
-- to full-service months would be a format effect, not comp growth).
-- Pattern: LAG period-over-period with eligibility flags.
-- Why it matters here: one location opened 2025-09 (ramp inflates naive
-- growth) and one converted 2025-07 (decline deflates it); naive and comp
-- answer different questions and only comp answers "how is the business
-- really doing".

WITH monthly AS (
    SELECT
        f.location_id,
        date_trunc('month', f.business_date)::date AS month_start,
        sum(f.net_amount)                          AS net_sales
    FROM marts.fact_ticket_line f
    GROUP BY f.location_id, date_trunc('month', f.business_date)
),
flagged AS (
    SELECT
        m.location_id,
        m.month_start,
        m.net_sales,
        lag(m.net_sales, 12) OVER (
            PARTITION BY m.location_id ORDER BY m.month_start
        ) AS net_sales_py,
        -- open 13 full months at both ends of the comparison
        (l.open_date <= m.month_start - interval '13 months'
         AND NOT EXISTS (
             SELECT 1
             FROM marts.dim_location_history h
             WHERE h.location_id = m.location_id
               AND h.valid_from > l.open_date          -- a later era exists =
               AND h.valid_from <= m.month_start       -- conversion happened
               AND h.valid_from + interval '12 months' > m.month_start - interval '12 months'
         )) AS comp_eligible
    FROM monthly m
    JOIN marts.dim_location l USING (location_id)
)
SELECT
    to_char(month_start, 'YYYY-MM')                                   AS month,
    round(100.0 * (sum(net_sales) / nullif(sum(net_sales_py), 0) - 1), 2)
        AS naive_yoy_pct,
    round(100.0 * (sum(net_sales) FILTER (WHERE comp_eligible)
                   / nullif(sum(net_sales_py) FILTER (WHERE comp_eligible), 0) - 1), 2)
        AS comp_yoy_pct,
    count(*) FILTER (WHERE comp_eligible)                             AS comp_locations
FROM flagged
WHERE net_sales_py IS NOT NULL
GROUP BY month_start
ORDER BY month_start;

-- H1-2026 summary: the number pair the executive summary quotes
WITH monthly AS (
    SELECT
        f.location_id,
        date_trunc('month', f.business_date)::date AS month_start,
        sum(f.net_amount)                          AS net_sales
    FROM marts.fact_ticket_line f
    GROUP BY 1, 2
),
h1 AS (
    SELECT
        location_id,
        sum(net_sales) FILTER (WHERE month_start BETWEEN date '2026-01-01' AND date '2026-06-01') AS h1_26,
        sum(net_sales) FILTER (WHERE month_start BETWEEN date '2025-01-01' AND date '2025-06-01') AS h1_25
    FROM monthly
    GROUP BY location_id
),
elig AS (
    SELECT
        h.*,
        (l.open_date <= date '2024-12-01'
         AND NOT EXISTS (SELECT 1 FROM marts.dim_location_history x
                         WHERE x.location_id = h.location_id
                           AND x.valid_from > l.open_date
                           AND x.valid_from >= date '2025-01-01')) AS comp_eligible
    FROM h1 h
    JOIN marts.dim_location l USING (location_id)
)
SELECT
    round(100.0 * (sum(h1_26) / sum(h1_25) - 1), 2)                            AS naive_h1_yoy_pct,
    round(100.0 * (sum(h1_26) FILTER (WHERE comp_eligible)
                   / sum(h1_25) FILTER (WHERE comp_eligible) - 1), 2)          AS comp_h1_yoy_pct,
    count(*) FILTER (WHERE comp_eligible)                                      AS comp_locations
FROM elig;
