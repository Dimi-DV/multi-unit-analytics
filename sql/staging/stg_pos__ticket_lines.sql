-- staging.stg_pos__ticket_lines: 1:1 over raw.pos_ticket_lines.
-- Typing is the first transformation: three business_date formats are parsed,
-- the spring-2025 UTC export window is normalized back to local wall time, and
-- export_seq marks re-fired duplicates (1 = latest export of a line; the mart
-- keeps only export_seq = 1). No business logic here; the net-sales rule is
-- applied once, in marts.fact_ticket_line.

CREATE OR REPLACE VIEW staging.stg_pos__ticket_lines AS
WITH typed AS (
    SELECT
        location_code,
        CASE
            WHEN business_date ~ '^\d{4}-\d{2}-\d{2}$'
                THEN business_date::date
            WHEN business_date ~ '^\d{1,2}/\d{1,2}/\d{4}$'
                THEN to_date(business_date, 'MM/DD/YYYY')
            WHEN business_date ~ '^\d{4}/\d{2}/\d{2}$'
                THEN to_date(business_date, 'YYYY/MM/DD')
        END                           AS business_date,
        ticket_number::integer        AS ticket_number,
        line_number::smallint         AS line_number,
        CASE
            WHEN closed_at LIKE '%Z'
                THEN (closed_at::timestamptz AT TIME ZONE 'America/New_York')
            ELSE closed_at::timestamp
        END                           AS closed_at,
        item_name,
        qty::integer                  AS qty,
        unit_price::numeric(9,2)      AS unit_price,
        discount_amount::numeric(9,2) AS discount_amount,
        line_state,
        order_mode
    FROM raw.pos_ticket_lines
)
SELECT
    typed.*,
    row_number() OVER (
        PARTITION BY location_code, business_date, ticket_number, line_number
        ORDER BY closed_at DESC
    ) AS export_seq
FROM typed;
