-- 08 | Consecutive weeks above the prime-cost threshold (gap-and-islands)
--
-- Business question: what is the longest consecutive-week streak each
-- location spent above the 62% prime-cost threshold?
-- Basis: rolling 4-week prime cost by ISO week. Weekly purchase-based COGS is
-- delivery-day lumpy (a Thursday beef drop lands a week of cost in one week),
-- so single-week prime cost manufactures phantom islands; the rolling window
-- is the documented smoothing choice, and the memo quotes it as such.
-- Pattern: gap-and-islands via row_number difference over flagged weeks.

WITH weekly AS (
    SELECT
        location_id,
        date_trunc('week', business_date)::date AS week_start,
        sum(net_amount)                         AS net_sales
    FROM marts.fact_ticket_line
    GROUP BY 1, 2
),
weekly_cogs AS (
    SELECT
        location_id,
        date_trunc('week', invoice_date)::date AS week_start,
        sum(ext_cost)                          AS purchases
    FROM marts.fact_invoice_line
    GROUP BY 1, 2
),
weekly_labor AS (
    SELECT
        location_id,
        date_trunc('week', business_date)::date AS week_start,
        sum(wages)                              AS labor_cost
    FROM marts.fact_labor_day
    GROUP BY 1, 2
),
rolled AS (
    SELECT
        w.location_id,
        w.week_start,
        sum(w.net_sales) OVER w4                          AS net_4w,
        sum(COALESCE(c.purchases, 0)) OVER w4             AS cogs_4w,
        sum(COALESCE(b.labor_cost, 0)) OVER w4            AS labor_4w,
        count(*) OVER w4                                  AS weeks_in_window
    FROM weekly w
    LEFT JOIN weekly_cogs c USING (location_id, week_start)
    LEFT JOIN weekly_labor b USING (location_id, week_start)
    WINDOW w4 AS (PARTITION BY w.location_id ORDER BY w.week_start
                  ROWS BETWEEN 3 PRECEDING AND CURRENT ROW)
),
flagged AS (
    SELECT
        location_id,
        week_start,
        (100.0 * (cogs_4w + labor_4w) / net_4w) > 62.0 AS over_threshold
    FROM rolled
    WHERE weeks_in_window = 4 AND net_4w > 0
),
islands AS (
    SELECT
        location_id,
        week_start,
        row_number() OVER (PARTITION BY location_id ORDER BY week_start)
        - row_number() OVER (PARTITION BY location_id, over_threshold ORDER BY week_start)
            AS island_id
    FROM flagged
    WHERE over_threshold
)
SELECT
    l.location_code,
    min(i.week_start) AS streak_start,
    max(i.week_start) AS streak_end,
    count(*)          AS weeks
FROM islands i
JOIN marts.dim_location l USING (location_id)
GROUP BY l.location_code, i.island_id
HAVING count(*) >= 4
ORDER BY weeks DESC, l.location_code;
