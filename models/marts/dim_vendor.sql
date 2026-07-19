{{ config(post_hook=[
    "alter table {{ this }} add primary key (vendor_id)"
]) }}
select vendor_id, vendor_name, vendor_category
from {{ ref('stg_ap__vendors') }}
