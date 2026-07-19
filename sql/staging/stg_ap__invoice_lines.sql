-- staging.stg_ap__invoice_lines: types, unit-of-measure normalization, and a
-- documented backfill: where unit_cost arrived blank but ext_cost and qty are
-- present, unit_cost_filled back-calculates it; the raw NULL is preserved in
-- unit_cost so the imputation is always visible.

CREATE OR REPLACE VIEW staging.stg_ap__invoice_lines AS
SELECT
    invoice_number,
    line_number::smallint               AS line_number,
    location_code,
    vendor_name,
    invoice_date::date                  AS invoice_date,
    posted_date::date                   AS posted_date,
    item_desc,
    qty::numeric(9,3)                   AS qty,
    CASE lower(trim(uom))
        WHEN 'case' THEN 'CS'
        WHEN 'lb'   THEN 'LB'
        WHEN 'ea'   THEN 'EA'
        WHEN 'bag'  THEN 'BG'
        ELSE upper(trim(uom))
    END                                 AS uom,
    NULLIF(unit_cost, '')::numeric(9,4) AS unit_cost,
    COALESCE(
        NULLIF(unit_cost, '')::numeric(9,4),
        round(ext_cost::numeric / NULLIF(qty::numeric, 0), 4)
    )                                   AS unit_cost_filled,
    ext_cost::numeric(12,2)             AS ext_cost
FROM raw.ap_invoice_lines;
