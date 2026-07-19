-- 07 | Daypart performance and staffing questions
--
-- Business question: which dayparts carry each location, which underperform
-- against format peers, and what happened to the converted store's dinner
-- daypart? Also: the beverage-attach gap, which is nearly pure margin.
-- Pattern: filter + aggregate + HAVING over a location x daypart grid.
-- Late-night wraps midnight and posts to the prior service date by the
-- business-date convention, so daypart shares always sum to 100 per day.

-- The grid: share of net sales by daypart, per location, trailing 12 months
WITH grid AS (
    SELECT
        l.location_code,
        l.service_format,
        f.daypart,
        sum(f.net_amount) AS net_sales
    FROM marts.fact_ticket_line f
    JOIN marts.dim_location l USING (location_id)
    WHERE f.business_date BETWEEN date '2025-07-01' AND date '2026-06-30'
    GROUP BY 1, 2, 3
)
SELECT
    location_code,
    daypart,
    round(100.0 * net_sales / sum(net_sales) OVER (PARTITION BY location_code), 1)
        AS share_pct,
    round(net_sales, 0) AS net_sales
FROM grid
ORDER BY location_code,
         CASE daypart WHEN 'breakfast' THEN 1 WHEN 'lunch' THEN 2
                      WHEN 'afternoon' THEN 3 WHEN 'dinner' THEN 4 ELSE 5 END;

-- Flagged cells: dayparts running under half their format-peer average share
WITH grid AS (
    SELECT
        l.location_code,
        l.service_format,
        f.daypart,
        sum(f.net_amount) AS net_sales
    FROM marts.fact_ticket_line f
    JOIN marts.dim_location l USING (location_id)
    WHERE f.business_date BETWEEN date '2025-07-01' AND date '2026-06-30'
    GROUP BY 1, 2, 3
),
shares AS (
    SELECT
        location_code, service_format, daypart,
        100.0 * net_sales / sum(net_sales) OVER (PARTITION BY location_code) AS share_pct
    FROM grid
)
SELECT
    s.location_code,
    s.daypart,
    round(s.share_pct, 1)      AS share_pct,
    round(avg(p.share_pct), 1) AS format_peer_avg_pct
FROM shares s
JOIN shares p ON p.service_format = s.service_format
            AND p.daypart = s.daypart
            AND p.location_code <> s.location_code
GROUP BY s.location_code, s.daypart, s.share_pct
HAVING s.share_pct < 0.5 * avg(p.share_pct)
ORDER BY s.location_code;

-- The converted store's dinner daypart, before vs after conversion
SELECT
    h.service_format,
    round(sum(f.net_amount) FILTER (WHERE f.daypart = 'dinner')
          / count(DISTINCT f.business_date), 0) AS dinner_net_per_day,
    round(100.0 * sum(f.net_amount) FILTER (WHERE f.daypart = 'dinner')
          / sum(f.net_amount), 1)               AS dinner_share_pct
FROM marts.fact_ticket_line f
JOIN marts.dim_location_history h
  ON h.location_id = f.location_id
 AND f.business_date >= h.valid_from
 AND f.business_date <= COALESCE(h.valid_to, date '9999-12-31')
WHERE f.location_id = (SELECT location_id FROM marts.dim_location WHERE location_code = 'CW-GCX')
GROUP BY h.service_format
ORDER BY 1;

-- NA-beverage attach by location, trailing 12 months (tickets with a sale)
WITH t AS (
    SELECT
        f.location_id,
        f.business_date,
        f.ticket_number,
        bool_or(m.category = 'NA Beverages' AND f.line_state = 'sale') AS has_na,
        bool_or(f.line_state = 'sale')                                 AS has_sale
    FROM marts.fact_ticket_line f
    JOIN marts.dim_menu_item m USING (menu_item_id)
    WHERE f.business_date BETWEEN date '2025-07-01' AND date '2026-06-30'
    GROUP BY 1, 2, 3
)
SELECT
    l.location_code,
    round(100.0 * count(*) FILTER (WHERE has_na) / count(*), 1) AS na_attach_pct
FROM t
JOIN marts.dim_location l USING (location_id)
WHERE has_sale
GROUP BY l.location_code
ORDER BY na_attach_pct;
