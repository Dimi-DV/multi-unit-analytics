-- Location x month plan; rows begin at each location's first full open month.
{{ config(post_hook=[
    "alter table {{ this }} add primary key (location_id, month_start)"
]) }}
select
    b.location_id::smallint as location_id,
    p.month_start,
    p.net_sales_budget,
    p.cogs_budget,
    p.labor_budget
from {{ ref('stg_plan__budget') }} p
join {{ source('ref', 'location_bridge') }} b on b.location_code = p.location_code
