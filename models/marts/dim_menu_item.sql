-- One row per canonical menu item (46). NULL costs preserved; imputation is
-- an analysis decision (see analysis/06).
{{ config(post_hook=[
    "alter table {{ this }} add primary key (menu_item_id)"
]) }}
select
    menu_item_id,
    item_name,
    category,
    standard_price,
    theoretical_unit_cost
from {{ ref('stg_pos__menu_items') }}
