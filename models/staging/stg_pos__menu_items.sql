-- staging.stg_pos__menu_items: types plus category normalization (casing and
-- whitespace drift in the export). NULL theoretical costs stay NULL: whether
-- and how to impute is an analysis decision, not a staging one.

SELECT
    menu_item_id::smallint                          AS menu_item_id,
    item_name,
    CASE lower(trim(category))
        WHEN 'na beverages' THEN 'NA Beverages'
        ELSE initcap(trim(category))
    END                                             AS category,
    standard_price::numeric(7,2)                    AS standard_price,
    NULLIF(theoretical_unit_cost, '')::numeric(7,4) AS theoretical_unit_cost
FROM {{ source('pos', 'menu_items') }}
