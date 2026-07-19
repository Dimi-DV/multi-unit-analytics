-- marts.dim_location_history: one row per location-code era (10 rows).
-- Format-aware analysis range-joins on valid_from/valid_to; everything else
-- ignores this table and stays simple.

DROP TABLE IF EXISTS marts.dim_location_history CASCADE;
CREATE TABLE marts.dim_location_history (
    location_id    smallint NOT NULL REFERENCES marts.dim_location,
    location_code  text NOT NULL,          -- POS code in force during this era
    service_format text NOT NULL CHECK (service_format IN ('full_service', 'counter_service')),
    volume_tier    text NOT NULL,
    seats          smallint NOT NULL,
    valid_from     date NOT NULL,
    valid_to       date,                   -- NULL = current
    PRIMARY KEY (location_id, valid_from)
);

INSERT INTO marts.dim_location_history
SELECT
    b.location_id::smallint,
    l.location_code,
    l.service_format,
    l.volume_tier,
    l.seats,
    l.open_date,
    l.closed_date
FROM staging.stg_pos__locations l
JOIN raw.ref_location_bridge b ON b.location_code = l.location_code;
