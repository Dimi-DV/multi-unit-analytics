-- staging.stg_gl__daily_sales: types over raw.gl_daily_sales (finance book,
-- canonical location codes throughout).

CREATE OR REPLACE VIEW staging.stg_gl__daily_sales AS
SELECT
    business_date::date        AS business_date,
    location_code,
    gl_net_sales::numeric(12,2) AS gl_net_sales
FROM raw.gl_daily_sales;
