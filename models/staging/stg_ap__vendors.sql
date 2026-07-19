-- staging.stg_ap__vendors: types over {{ source('ap', 'vendors') }}.

SELECT
    vendor_id::smallint AS vendor_id,
    vendor_name,
    vendor_category
FROM {{ source('ap', 'vendors') }}
