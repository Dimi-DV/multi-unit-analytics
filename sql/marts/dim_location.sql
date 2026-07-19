-- marts.dim_location: strictly one row per physical location (9), carrying
-- current attributes so every basic join stays simple. History (the mid-2025
-- format conversion and POS re-key) lives only in dim_location_history.
-- borough supports the location -> borough -> group hierarchy rollup.

DROP TABLE IF EXISTS marts.dim_location CASCADE;
CREATE TABLE marts.dim_location (
    location_id    smallint PRIMARY KEY,
    location_code  text NOT NULL UNIQUE,   -- current POS code
    location_name  text NOT NULL,
    neighborhood   text NOT NULL,
    borough        text NOT NULL CHECK (borough IN ('Manhattan', 'Brooklyn', 'Queens')),
    service_format text NOT NULL CHECK (service_format IN ('full_service', 'counter_service')),
    volume_tier    text NOT NULL CHECK (volume_tier IN ('T1', 'T2', 'T3', 'T4')),
    seats          smallint NOT NULL CHECK (seats > 0),
    open_date      date NOT NULL           -- drives same-store eligibility
);

INSERT INTO marts.dim_location
SELECT
    b.location_id::smallint,
    l.location_code,
    l.location_name,
    l.neighborhood,
    l.borough,
    l.service_format,
    l.volume_tier,
    l.seats,
    -- the physical location's first open date, not the current era's
    min(l2.open_date)
FROM staging.stg_pos__locations l
JOIN raw.ref_location_bridge b ON b.location_code = l.location_code
JOIN raw.ref_location_bridge b2 ON b2.location_id = b.location_id
JOIN staging.stg_pos__locations l2 ON l2.location_code = b2.location_code
WHERE l.closed_date IS NULL   -- current era only
GROUP BY 1, 2, 3, 4, 5, 6, 7, 8;
