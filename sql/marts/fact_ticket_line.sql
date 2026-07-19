-- marts.fact_ticket_line: one deduplicated POS ticket line (~4.85M rows).
-- This is where the cleaning contract lands, applied exactly once:
--   dedup-keep-latest (export_seq = 1 from staging),
--   dish-name drift resolved through the alias map (total inner join; the
--     zero-row anti-join audit lives in analysis/03),
--   both location-code eras bridged to one location_id,
--   the net-sales rule: sales net of discounts, refunds negative, voids and
--     comps zero,
--   daypart and brunch flags materialized (late-night wraps midnight and posts
--     to the prior service date, which business_date already carries).
-- The composite PK doubles as the dedup regression test: wrong dedup logic
-- upstream makes this build fail loudly.

DROP TABLE IF EXISTS marts.fact_ticket_line CASCADE;
CREATE TABLE marts.fact_ticket_line (
    location_id     smallint NOT NULL REFERENCES marts.dim_location,
    business_date   date NOT NULL REFERENCES marts.dim_date,
    ticket_number   integer NOT NULL,
    line_number     smallint NOT NULL,
    closed_at       timestamp NOT NULL,
    daypart         text NOT NULL CHECK (daypart IN
        ('breakfast', 'lunch', 'afternoon', 'dinner', 'late_night')),
    is_brunch       boolean NOT NULL,
    menu_item_id    smallint NOT NULL REFERENCES marts.dim_menu_item,
    qty             integer NOT NULL,
    unit_price      numeric(9,2) NOT NULL,
    discount_amount numeric(9,2) NOT NULL DEFAULT 0,
    line_state      text NOT NULL CHECK (line_state IN ('sale', 'void', 'comp', 'refund')),
    order_mode      text NOT NULL CHECK (order_mode IN ('DI', 'TO', 'DL')),
    gross_amount    numeric(11,2) NOT NULL,
    net_amount      numeric(11,2) NOT NULL,
    PRIMARY KEY (location_id, business_date, ticket_number, line_number),
    -- net can never drift from its definition once materialized
    CHECK (line_state NOT IN ('sale', 'refund')
           OR net_amount = gross_amount - CASE WHEN line_state = 'sale'
                                               THEN discount_amount ELSE 0 END),
    CHECK (line_state NOT IN ('void', 'comp') OR net_amount = 0)
);

INSERT INTO marts.fact_ticket_line
SELECT
    b.location_id::smallint,
    t.business_date,
    t.ticket_number,
    t.line_number,
    t.closed_at,
    CASE
        WHEN extract(hour FROM t.closed_at) BETWEEN 7 AND 10  THEN 'breakfast'
        WHEN extract(hour FROM t.closed_at) BETWEEN 11 AND 14 THEN 'lunch'
        WHEN extract(hour FROM t.closed_at) BETWEEN 15 AND 16 THEN 'afternoon'
        WHEN extract(hour FROM t.closed_at) BETWEEN 17 AND 21 THEN 'dinner'
        ELSE 'late_night'   -- 22:00-01:59, wraps midnight on the service date
    END,
    (extract(isodow FROM t.business_date) IN (6, 7)
     AND extract(hour FROM t.closed_at) BETWEEN 10 AND 14),
    a.menu_item_id::smallint,
    t.qty,
    t.unit_price,
    t.discount_amount,
    t.line_state,
    t.order_mode,
    (t.qty * t.unit_price)::numeric(11,2),
    CASE t.line_state
        WHEN 'sale'   THEN (t.qty * t.unit_price - t.discount_amount)::numeric(11,2)
        WHEN 'refund' THEN (t.qty * t.unit_price)::numeric(11,2)
        ELSE 0
    END
FROM staging.stg_pos__ticket_lines t
JOIN raw.ref_location_bridge b ON b.location_code = t.location_code
-- The alias map can carry case-only variants of the same name; joining it raw
-- would fan out. Consumption always goes through the set made distinct on the
-- normalized key (uniqueness audited in analysis/03).
JOIN (
    SELECT DISTINCT lower(trim(alias)) AS alias_norm, menu_item_id
    FROM raw.ref_item_aliases
) a ON a.alias_norm = lower(trim(t.item_name))
WHERE t.export_seq = 1;

CREATE INDEX idx_ftl_business_date ON marts.fact_ticket_line (business_date);
CREATE INDEX idx_ftl_menu_item ON marts.fact_ticket_line (menu_item_id);
ANALYZE marts.fact_ticket_line;
