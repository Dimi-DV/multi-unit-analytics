-- Every POS item name, drifted or not, must resolve through the alias map
-- (the anti-join audit from analysis/03, promoted to a standing test).
select distinct t.item_name
from {{ ref('stg_pos__ticket_lines') }} t
left join {{ source('ref', 'item_aliases') }} a
       on lower(trim(a.alias)) = lower(trim(t.item_name))
where a.alias is null
