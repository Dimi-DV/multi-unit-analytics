-- 02 | Duplicate (re-fired) ticket cleanup and impact
--
-- Business question: how much would duplicate re-fired tickets have inflated
-- reported sales if nobody deduplicated, and where did they cluster?
-- Pattern: dedup-keep-latest. Duplicates share the full business key
-- (location, business date, ticket, line) and differ only in closed_at; the
-- staging view ranks exports per key and the mart keeps rank 1. This query
-- runs against staging to show the duplicates the mart already removed.

WITH ranked AS (
    SELECT
        t.location_code,
        t.business_date,
        t.qty * t.unit_price - t.discount_amount AS would_be_net,
        t.line_state,
        t.export_seq
    FROM staging.stg_pos__ticket_lines t
)
SELECT
    b.location_id,
    to_char(date_trunc('month', r.business_date), 'YYYY-MM')      AS month,
    count(*)                                                       AS duplicate_lines,
    sum(r.would_be_net) FILTER (WHERE r.line_state = 'sale')       AS inflated_net,
    round(100.0 * sum(r.would_be_net) FILTER (WHERE r.line_state = 'sale')
          / nullif(sum(f.net) , 0), 3)                             AS inflation_pct
FROM ranked r
JOIN raw.ref_location_bridge b ON b.location_code = r.location_code
JOIN LATERAL (
    SELECT sum(net_amount) AS net
    FROM marts.fact_ticket_line
    WHERE location_id = b.location_id::smallint
      AND business_date >= date_trunc('month', r.business_date)
      AND business_date < date_trunc('month', r.business_date) + interval '1 month'
) f ON true
WHERE r.export_seq > 1
GROUP BY b.location_id, date_trunc('month', r.business_date)
ORDER BY duplicate_lines DESC;
