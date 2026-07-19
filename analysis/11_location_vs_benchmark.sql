-- 11 | Each location vs the group benchmark
--
-- Business question: how does each location-month compare to the group, and
-- does the converted store read correctly through its two location-code eras?
-- Pattern: self-join / hierarchy. The benchmark join is a self-aggregation;
-- the rollup walks a real location -> borough -> group hierarchy with a
-- recursive CTE (borough lives on dim_location, so the hierarchy is honest,
-- not decorative).

-- Location-month vs group benchmark (same month, all locations)
WITH monthly AS (
    SELECT
        f.location_id,
        date_trunc('month', f.business_date)::date AS month_start,
        sum(f.net_amount)                          AS net_sales
    FROM marts.fact_ticket_line f
    GROUP BY 1, 2
)
SELECT
    l.location_code,
    to_char(m.month_start, 'YYYY-MM')                       AS month,
    round(m.net_sales, 0)                                   AS net_sales,
    round(g.group_avg, 0)                                   AS group_avg_per_location,
    round(100.0 * (m.net_sales / g.group_avg - 1), 1)       AS vs_group_pct
FROM monthly m
JOIN marts.dim_location l USING (location_id)
JOIN (
    SELECT month_start, avg(net_sales) AS group_avg
    FROM monthly
    GROUP BY month_start
) g USING (month_start)
WHERE m.month_start IN (date '2025-06-01', date '2025-07-01', date '2026-06-01')
ORDER BY m.month_start, vs_group_pct DESC;

-- Hierarchy rollup: location -> borough -> group via recursive CTE, trailing 12 months
WITH RECURSIVE nodes AS (
    SELECT 'group'::text AS node, NULL::text AS parent FROM (VALUES (1)) v
    UNION ALL
    SELECT DISTINCT borough, 'group' FROM marts.dim_location
    UNION ALL
    SELECT location_code, borough FROM marts.dim_location
),
leaf_sales AS (
    SELECT l.location_code AS node, sum(f.net_amount) AS net_sales
    FROM marts.fact_ticket_line f
    JOIN marts.dim_location l USING (location_id)
    WHERE f.business_date BETWEEN date '2025-07-01' AND date '2026-06-30'
    GROUP BY l.location_code
),
walk AS (
    -- every leaf contributes to itself and each ancestor
    SELECT n.node AS leaf, n.node, n.parent
    FROM nodes n
    WHERE n.node IN (SELECT node FROM leaf_sales)
    UNION ALL
    SELECT w.leaf, n.node, n.parent
    FROM walk w
    JOIN nodes n ON n.node = w.parent
)
SELECT
    w.node,
    round(sum(s.net_sales), 0) AS net_sales_t12,
    count(DISTINCT w.leaf)     AS locations
FROM walk w
JOIN leaf_sales s ON s.node = w.leaf
GROUP BY w.node
ORDER BY net_sales_t12 DESC;

-- The conversion verdict: the same physical store, era vs era, per open day
SELECT
    h.location_code                                        AS era_code,
    h.service_format,
    round(sum(f.net_amount) / count(DISTINCT f.business_date), 0) AS net_per_open_day,
    round(sum(f.net_amount), 0)                            AS net_total,
    count(DISTINCT f.business_date)                        AS open_days
FROM marts.fact_ticket_line f
JOIN marts.dim_location_history h
  ON h.location_id = f.location_id
 AND f.business_date >= h.valid_from
 AND f.business_date <= COALESCE(h.valid_to, date '9999-12-31')
WHERE f.location_id = (SELECT location_id FROM marts.dim_location WHERE location_code = 'CW-GCX')
GROUP BY h.location_code, h.service_format
ORDER BY min(h.valid_from);
