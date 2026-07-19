# Schema context, raw condition

Postgres 16. Schema `raw`: unmodeled POS/AP/labor/GL exports for a fictional
9-location NYC restaurant group, 2024-01-01 through 2026-06-30. **Every column
is TEXT.** Known data conditions: `pos_ticket_lines.business_date` arrives in
three formats (YYYY-MM-DD, M/D/YYYY, YYYY/MM/DD); some `closed_at` values are
UTC ISO-8601 with a Z suffix; re-fired duplicate lines share
(location_code, business_date, ticket_number, line_number) and differ only in
closed_at; dish names drift (misspellings, truncations, casings) and
`ref_item_aliases` maps every observed spelling to a menu_item_id; one store
was re-keyed from CW-GC to CW-GCX on 2025-07-01 and `ref_location_bridge` maps
10 codes to 9 location_ids; finance feeds (gl_daily_sales, labor_daily,
ap_invoice_lines, plan_budget) use canonical codes throughout; voids/comps
carry line_state and do not count toward net sales, refunds count negative.

Tables and columns:

- `raw.pos_ticket_lines(location_code, business_date, ticket_number,
  line_number, closed_at, item_name, qty, unit_price, discount_amount,
  line_state, order_mode)`
- `raw.pos_locations(location_code, location_name, neighborhood, borough,
  service_format, volume_tier, seats, open_date, closed_date)` - 10 rows
- `raw.pos_menu_items(menu_item_id, item_name, category, standard_price,
  theoretical_unit_cost)` - categories carry casing typos
- `raw.ap_invoice_lines(invoice_number, line_number, location_code,
  vendor_name, invoice_date, posted_date, item_desc, qty, uom, unit_cost,
  ext_cost)` - some unit_cost blank, uom casing varies
- `raw.ap_vendors(vendor_id, vendor_name, vendor_category)`
- `raw.labor_daily(business_date, location_code, role, hours, wages)` - role
  casing varies
- `raw.gl_daily_sales(business_date, location_code, gl_net_sales)`
- `raw.plan_budget(month_start, location_code, net_sales_budget, cogs_budget,
  labor_budget)`
- `raw.ref_calendar(date_day, year, quarter, month, month_name, day_of_week,
  day_name, is_weekend, is_holiday, holiday_name, holiday_type,
  is_school_break, is_dining_week, is_marathon_sunday)`
- `raw.ref_dayparts(daypart, start_time, end_time)`
- `raw.ref_item_aliases(alias, menu_item_id)`
- `raw.ref_location_bridge(location_code, location_id)`

Cast whatever you need; nothing is typed for you.
