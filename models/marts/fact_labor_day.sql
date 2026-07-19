-- Location x business date x role; payroll never re-keyed with the POS, and
-- role casing variants collapse under normalization, so the model sums to its
-- grain and the post-hook key enforces it.
{{ config(post_hook=[
    "alter table {{ this }} add primary key (location_id, business_date, role)",
    "analyze {{ this }}"
]) }}
select
    b.location_id::smallint as location_id,
    l.business_date,
    l.role,
    sum(l.hours)            as hours,
    sum(l.wages)            as wages
from {{ ref('stg_labor__daily') }} l
join {{ source('ref', 'location_bridge') }} b on b.location_code = l.location_code
group by 1, 2, 3
