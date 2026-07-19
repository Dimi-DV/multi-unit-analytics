-- Finance's daily net sales. Outside the injected variance windows this ties
-- to cleaned POS net sales to the penny (analysis/09; bounded by a singular test).
{{ config(post_hook=[
    "alter table {{ this }} add primary key (location_id, business_date)"
]) }}
select
    b.location_id::smallint as location_id,
    g.business_date,
    g.gl_net_sales
from {{ ref('stg_gl__daily_sales') }} g
join {{ source('ref', 'location_bridge') }} b on b.location_code = g.location_code
