-- One row per location-code era (10). Format-aware analysis range-joins on
-- valid_from/valid_to; everything else ignores this table.
{{ config(post_hook=[
    "alter table {{ this }} add primary key (location_id, valid_from)"
]) }}
select
    b.location_id::smallint  as location_id,
    l.location_code,
    l.service_format,
    l.volume_tier,
    l.seats,
    l.open_date              as valid_from,
    l.closed_date            as valid_to
from {{ ref('stg_pos__locations') }} l
join {{ source('ref', 'location_bridge') }} b on b.location_code = l.location_code
