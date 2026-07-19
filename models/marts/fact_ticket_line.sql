-- One deduplicated POS ticket line. The cleaning contract, applied once:
-- dedup-keep-latest (export_seq = 1), alias map consumed distinct on the
-- normalized key, both location-code eras bridged, the net-sales rule, and
-- daypart/brunch materialized. The post-hook primary key doubles as the dedup
-- regression test: wrong dedup upstream fails this build loudly. The check
-- constraints keep net_amount from ever drifting from its definition.
{{ config(
    indexes=[
        {'columns': ['business_date']},
        {'columns': ['menu_item_id']}
    ],
    post_hook=[
        "alter table {{ this }} add primary key (location_id, business_date, ticket_number, line_number)",
        "alter table {{ this }} add constraint net_rule_sale_refund check (line_state not in ('sale', 'refund') or net_amount = gross_amount - case when line_state = 'sale' then discount_amount else 0 end)",
        "alter table {{ this }} add constraint net_rule_void_comp check (line_state not in ('void', 'comp') or net_amount = 0)",
        "analyze {{ this }}"
    ]
) }}
with alias_map as (
    -- case-only variants of one name must not fan out the join
    select distinct lower(trim(alias)) as alias_norm, menu_item_id
    from {{ source('ref', 'item_aliases') }}
)
select
    b.location_id::smallint          as location_id,
    t.business_date,
    t.ticket_number,
    t.line_number,
    t.closed_at,
    case
        when extract(hour from t.closed_at) between 7 and 10  then 'breakfast'
        when extract(hour from t.closed_at) between 11 and 14 then 'lunch'
        when extract(hour from t.closed_at) between 15 and 16 then 'afternoon'
        when extract(hour from t.closed_at) between 17 and 21 then 'dinner'
        else 'late_night'
    end                              as daypart,
    (extract(isodow from t.business_date) in (6, 7)
     and extract(hour from t.closed_at) between 10 and 14) as is_brunch,
    a.menu_item_id::smallint         as menu_item_id,
    t.qty,
    t.unit_price,
    t.discount_amount,
    t.line_state,
    t.order_mode,
    (t.qty * t.unit_price)::numeric(11,2) as gross_amount,
    case t.line_state
        when 'sale'   then (t.qty * t.unit_price - t.discount_amount)::numeric(11,2)
        when 'refund' then (t.qty * t.unit_price)::numeric(11,2)
        else 0
    end                              as net_amount
from {{ ref('stg_pos__ticket_lines') }} t
join {{ source('ref', 'location_bridge') }} b on b.location_code = t.location_code
join alias_map a on a.alias_norm = lower(trim(t.item_name))
where t.export_seq = 1
