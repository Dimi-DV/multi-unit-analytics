-- One AP invoice line. COGS as purchases: a documented proxy, meaningful over
-- 4-plus-week windows (see docs/DATASET.md).
{{ config(post_hook=[
    "alter table {{ this }} add primary key (invoice_number, line_number)",
    "analyze {{ this }}"
]) }}
select
    i.invoice_number,
    i.line_number,
    b.location_id::smallint as location_id,
    v.vendor_id,
    i.invoice_date,
    i.posted_date,
    i.item_desc,
    i.qty,
    i.uom,
    i.unit_cost,
    i.unit_cost_filled,
    i.ext_cost
from {{ ref('stg_ap__invoice_lines') }} i
join {{ source('ref', 'location_bridge') }} b on b.location_code = i.location_code
join {{ ref('stg_ap__vendors') }} v on v.vendor_name = i.vendor_name
