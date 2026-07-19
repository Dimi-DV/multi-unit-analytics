-- marts.fact_invoice_line: one AP invoice line. Invoice numbers are
-- vendor-prefixed and globally unique, so the natural composite key holds.
-- COGS here is purchases, a documented proxy (no inventory counts): only
-- meaningful over 4-plus-week windows because delivery days are lumpy.

DROP TABLE IF EXISTS marts.fact_invoice_line CASCADE;
CREATE TABLE marts.fact_invoice_line (
    invoice_number text NOT NULL,
    line_number    smallint NOT NULL,
    location_id    smallint NOT NULL REFERENCES marts.dim_location,
    vendor_id      smallint NOT NULL REFERENCES marts.dim_vendor,
    invoice_date   date NOT NULL REFERENCES marts.dim_date,
    posted_date    date NOT NULL,
    item_desc      text NOT NULL,
    qty            numeric(9,3) NOT NULL,
    uom            text NOT NULL,
    unit_cost      numeric(9,4),           -- NULL preserved from the feed
    unit_cost_filled numeric(9,4) NOT NULL, -- documented backfill from ext/qty
    ext_cost       numeric(12,2) NOT NULL,
    PRIMARY KEY (invoice_number, line_number),
    CHECK (posted_date >= invoice_date)
);

INSERT INTO marts.fact_invoice_line
SELECT
    i.invoice_number,
    i.line_number,
    b.location_id::smallint,
    v.vendor_id,
    i.invoice_date,
    i.posted_date,
    i.item_desc,
    i.qty,
    i.uom,
    i.unit_cost,
    i.unit_cost_filled,
    i.ext_cost
FROM staging.stg_ap__invoice_lines i
JOIN raw.ref_location_bridge b ON b.location_code = i.location_code
JOIN marts.dim_vendor v ON v.vendor_name = i.vendor_name;

CREATE INDEX idx_fil_invoice_date ON marts.fact_invoice_line (invoice_date);
CREATE INDEX idx_fil_vendor ON marts.fact_invoice_line (vendor_id);
ANALYZE marts.fact_invoice_line;
