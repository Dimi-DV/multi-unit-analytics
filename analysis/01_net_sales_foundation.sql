-- 01 | True monthly net sales by location
--
-- Business question: what are real monthly net sales by location once voids,
-- comps and refunds are handled correctly, and which location-months have a
-- comp rate above 3% of gross?
-- Pattern: filter + aggregate + HAVING.
-- The net-sales rule is applied once in the mart; this query proves the
-- foundation every later query stands on, then surfaces the comp exceptions.

-- Monthly net sales by location
SELECT
    l.location_code,
    d.year,
    d.month,
    sum(f.net_amount)                                   AS net_sales,
    sum(f.gross_amount) FILTER (WHERE f.line_state = 'comp')    AS comp_gross,
    count(DISTINCT f.ticket_number)                     AS tickets
FROM marts.fact_ticket_line f
JOIN marts.dim_location l USING (location_id)
JOIN marts.dim_date d ON d.date_key = f.business_date
GROUP BY l.location_code, d.year, d.month
ORDER BY l.location_code, d.year, d.month;

-- Exception list: location-months where comps exceed 3% of gross sales value
SELECT
    l.location_code,
    d.year,
    d.month,
    round(100.0 * sum(f.gross_amount) FILTER (WHERE f.line_state = 'comp')
          / sum(f.gross_amount) FILTER (WHERE f.line_state = 'sale'), 2) AS comp_rate_pct,
    sum(f.gross_amount) FILTER (WHERE f.line_state = 'comp')             AS comp_gross
FROM marts.fact_ticket_line f
JOIN marts.dim_location l USING (location_id)
JOIN marts.dim_date d ON d.date_key = f.business_date
GROUP BY l.location_code, d.year, d.month
HAVING sum(f.gross_amount) FILTER (WHERE f.line_state = 'comp')
       > 0.03 * sum(f.gross_amount) FILTER (WHERE f.line_state = 'sale')
ORDER BY comp_rate_pct DESC;
