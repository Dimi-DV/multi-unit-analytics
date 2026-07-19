-- marts.fact_gl_day: finance's daily net sales by location. Outside the
-- injected variance windows this ties to cleaned POS net sales to the penny;
-- analysis/09 is the tie-out.

DROP TABLE IF EXISTS marts.fact_gl_day CASCADE;
CREATE TABLE marts.fact_gl_day (
    location_id   smallint NOT NULL REFERENCES marts.dim_location,
    business_date date NOT NULL REFERENCES marts.dim_date,
    gl_net_sales  numeric(12,2) NOT NULL,
    PRIMARY KEY (location_id, business_date)
);

INSERT INTO marts.fact_gl_day
SELECT
    b.location_id::smallint,
    g.business_date,
    g.gl_net_sales
FROM staging.stg_gl__daily_sales g
JOIN raw.ref_location_bridge b ON b.location_code = g.location_code;

ANALYZE marts.fact_gl_day;
