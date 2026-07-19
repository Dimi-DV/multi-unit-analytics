-- Sanity band: no location-month prime cost outside 35-90% of net sales.
-- Catches broken purchase derivation or labor scaling before an analyst does.
with monthly as (
    select location_id, date_trunc('month', business_date)::date as month_start,
           sum(net_amount) as net_sales
    from {{ ref('fact_ticket_line') }}
    group by 1, 2
),
cogs as (
    select location_id, date_trunc('month', invoice_date)::date as month_start,
           sum(ext_cost) as purchases
    from {{ ref('fact_invoice_line') }}
    group by 1, 2
),
labor as (
    select location_id, date_trunc('month', business_date)::date as month_start,
           sum(wages) as labor_cost
    from {{ ref('fact_labor_day') }}
    group by 1, 2
)
select m.location_id, m.month_start,
       round(100.0 * (coalesce(c.purchases, 0) + coalesce(l.labor_cost, 0))
             / m.net_sales, 2) as prime_pct
from monthly m
left join cogs c using (location_id, month_start)
left join labor l using (location_id, month_start)
where m.net_sales > 0
  and (100.0 * (coalesce(c.purchases, 0) + coalesce(l.labor_cost, 0)) / m.net_sales
       not between 35 and 90)
