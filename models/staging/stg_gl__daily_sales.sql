-- staging.stg_gl__daily_sales: types over {{ source('gl', 'daily_sales') }} (finance book,
-- canonical location codes throughout).

SELECT
    business_date::date        AS business_date,
    location_code,
    gl_net_sales::numeric(12,2) AS gl_net_sales
FROM {{ source('gl', 'daily_sales') }}
