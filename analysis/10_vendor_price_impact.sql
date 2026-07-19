-- 10 | Vendor price steps and COGS impact
--
-- Business question: when did the beef vendor's prices step up, by how much,
-- and what did each step do to COGS% by location given menu mix? A location
-- that over-indexes on beef items imports more of a beef increase than the
-- group average; that mix effect is the second leg of the decision memo.
-- Pattern: LAG on monthly unit price for step detection.

-- Step detection: month-over-month unit-cost moves >= 3% on any vendor item
WITH monthly_price AS (
    SELECT
        v.vendor_name,
        i.item_desc,
        date_trunc('month', i.invoice_date)::date AS month_start,
        round(avg(i.unit_cost_filled), 4)         AS avg_unit_cost
    FROM marts.fact_invoice_line i
    JOIN marts.dim_vendor v USING (vendor_id)
    GROUP BY 1, 2, 3
),
steps AS (
    SELECT
        vendor_name,
        item_desc,
        month_start,
        avg_unit_cost,
        lag(avg_unit_cost) OVER (PARTITION BY vendor_name, item_desc
                                 ORDER BY month_start) AS prev_cost
    FROM monthly_price
)
SELECT
    vendor_name,
    item_desc,
    to_char(month_start, 'YYYY-MM')                          AS step_month,
    prev_cost,
    avg_unit_cost,
    round(100.0 * (avg_unit_cost / prev_cost - 1), 1)        AS step_pct
FROM steps
WHERE prev_cost > 0
  AND abs(avg_unit_cost / prev_cost - 1) >= 0.03
ORDER BY vendor_name, item_desc, month_start;

-- Mix-weighted impact: purchases as % of net sales by location, the quarter
-- before the first step vs the quarter after the second step
WITH windows AS (
    SELECT 'pre'  AS era, date '2024-12-01' AS d1, date '2025-02-28' AS d2
    UNION ALL
    SELECT 'post' AS era, date '2025-09-01', date '2025-11-30'
),
net AS (
    SELECT w.era, f.location_id, sum(f.net_amount) AS net_sales
    FROM marts.fact_ticket_line f
    JOIN windows w ON f.business_date BETWEEN w.d1 AND w.d2
    GROUP BY 1, 2
),
purch AS (
    SELECT w.era, i.location_id, sum(i.ext_cost) AS purchases
    FROM marts.fact_invoice_line i
    JOIN windows w ON i.invoice_date BETWEEN w.d1 AND w.d2
    GROUP BY 1, 2
)
SELECT
    l.location_code,
    round(100.0 * max(p.purchases) FILTER (WHERE p.era = 'pre')
          / max(n.net_sales) FILTER (WHERE n.era = 'pre'), 2)  AS cogs_pct_pre,
    round(100.0 * max(p.purchases) FILTER (WHERE p.era = 'post')
          / max(n.net_sales) FILTER (WHERE n.era = 'post'), 2) AS cogs_pct_post,
    round(100.0 * max(p.purchases) FILTER (WHERE p.era = 'post')
          / max(n.net_sales) FILTER (WHERE n.era = 'post')
        - 100.0 * max(p.purchases) FILTER (WHERE p.era = 'pre')
          / max(n.net_sales) FILTER (WHERE n.era = 'pre'), 2)  AS delta_pts
FROM net n
JOIN purch p ON p.era = n.era AND p.location_id = n.location_id
JOIN marts.dim_location l ON l.location_id = n.location_id
GROUP BY l.location_code
ORDER BY delta_pts DESC;
