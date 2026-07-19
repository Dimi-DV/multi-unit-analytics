-- Strictly one row per physical location (9), current attributes; history
-- lives in dim_location_history. open_date is the location's first open date
-- across code eras (drives same-store eligibility).
{{ config(post_hook=[
    "alter table {{ this }} add primary key (location_id)"
]) }}
select
    b.location_id::smallint  as location_id,
    l.location_code,
    l.location_name,
    l.neighborhood,
    l.borough,
    l.service_format,
    l.volume_tier,
    l.seats,
    min(l2.open_date)        as open_date
from {{ ref('stg_pos__locations') }} l
join {{ source('ref', 'location_bridge') }} b on b.location_code = l.location_code
join {{ source('ref', 'location_bridge') }} b2 on b2.location_id = b.location_id
join {{ ref('stg_pos__locations') }} l2 on l2.location_code = b2.location_code
where l.closed_date is null
group by 1, 2, 3, 4, 5, 6, 7, 8
