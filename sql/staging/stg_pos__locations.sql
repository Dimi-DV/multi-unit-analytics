-- staging.stg_pos__locations: types over raw.pos_locations.
-- One row per location-code era (10 rows for 9 physical locations: the
-- converted store's POS reinstall issued a new code mid-2025).

CREATE OR REPLACE VIEW staging.stg_pos__locations AS
SELECT
    location_code,
    location_name,
    neighborhood,
    borough,
    service_format,
    volume_tier,
    seats::smallint               AS seats,
    open_date::date               AS open_date,
    NULLIF(closed_date, '')::date AS closed_date
FROM raw.pos_locations;
