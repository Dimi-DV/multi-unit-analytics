-- 09 | POS to GL daily tie-out
--
-- Business question: do POS net sales tie to the ledger daily? Cutoff rule:
-- revenue belongs to the business date (service date); late-closed tickets do
-- not move it, and late-night tickets already post to the prior service date.
-- Outside the known variance windows the tie-out is exact to the penny; this
-- query returns exceptions only and buckets them by shape, which is how a
-- reconciliation actually gets worked: pattern first, then cause.
-- Pattern: FULL OUTER JOIN + COALESCE (a missing side is a finding, not a
-- join accident).

WITH pos AS (
    SELECT location_id, business_date, sum(net_amount) AS pos_net
    FROM marts.fact_ticket_line
    GROUP BY 1, 2
),
tie AS (
    SELECT
        COALESCE(p.location_id, g.location_id)     AS location_id,
        COALESCE(p.business_date, g.business_date) AS business_date,
        COALESCE(p.pos_net, 0)                     AS pos_net,
        COALESCE(g.gl_net_sales, 0)                AS gl_net,
        COALESCE(g.gl_net_sales, 0) - COALESCE(p.pos_net, 0) AS variance
    FROM pos p
    FULL OUTER JOIN marts.fact_gl_day g USING (location_id, business_date)
)
SELECT
    l.location_code,
    t.business_date,
    t.pos_net,
    t.gl_net,
    t.variance,
    CASE
        WHEN t.gl_net = 0 AND t.pos_net > 0 THEN 'gl_missing_day'
        WHEN abs(t.variance) <= 5           THEN 'rounding'
        WHEN t.variance < 0                 THEN 'gl_under_pos'
        ELSE 'gl_over_pos'
    END AS bucket
FROM tie t
JOIN marts.dim_location l USING (location_id)
WHERE t.variance <> 0
ORDER BY l.location_code, t.business_date;

-- Summary: variance days per location vs perfectly tied days
WITH pos AS (
    SELECT location_id, business_date, sum(net_amount) AS pos_net
    FROM marts.fact_ticket_line
    GROUP BY 1, 2
)
SELECT
    l.location_code,
    count(*) FILTER (WHERE g.gl_net_sales = p.pos_net)  AS tied_days,
    count(*) FILTER (WHERE g.gl_net_sales <> p.pos_net) AS variance_days
FROM pos p
JOIN marts.fact_gl_day g USING (location_id, business_date)
JOIN marts.dim_location l USING (location_id)
GROUP BY l.location_code
ORDER BY variance_days DESC;
