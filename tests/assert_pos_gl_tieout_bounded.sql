-- The GL must tie to cleaned POS net sales except on the injected variance
-- days (about 34: two deposit-shift windows, one missing day, one rounding
-- window, six corrected mis-keys). More than 45 variance days means the
-- net-sales rule or the ledger derivation broke. Fails by returning a row.
with pos as (
    select location_id, business_date, sum(net_amount) as pos_net
    from {{ ref('fact_ticket_line') }}
    group by 1, 2
)
select count(*) as variance_days
from pos p
join {{ ref('fact_gl_day') }} g using (location_id, business_date)
where g.gl_net_sales <> p.pos_net
having count(*) > 45
