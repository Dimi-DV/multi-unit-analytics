-- staging.stg_ap__vendors: types over raw.ap_vendors.

CREATE OR REPLACE VIEW staging.stg_ap__vendors AS
SELECT
    vendor_id::smallint AS vendor_id,
    vendor_name,
    vendor_category
FROM raw.ap_vendors;
