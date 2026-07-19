-- marts.dim_vendor: one row per vendor house (9).

DROP TABLE IF EXISTS marts.dim_vendor CASCADE;
CREATE TABLE marts.dim_vendor (
    vendor_id       smallint PRIMARY KEY,
    vendor_name     text NOT NULL UNIQUE,
    vendor_category text NOT NULL
);

INSERT INTO marts.dim_vendor
SELECT vendor_id, vendor_name, vendor_category
FROM staging.stg_ap__vendors;
