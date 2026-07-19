# Schema context given to the model

Postgres 16. Analytics schema `marts` for a fictional 9-location NYC
restaurant group (Copperwick), 2024-01-01 through 2026-06-30.

- `marts.dim_location(location_id PK, location_code, location_name,
  neighborhood, borough, service_format[full_service|counter_service],
  volume_tier[T1..T4], seats, open_date)`: one row per physical location (9).
- `marts.dim_location_history(location_id, location_code, service_format,
  volume_tier, seats, valid_from, valid_to)`: one row per location-code era
  (10; one store converted formats and was re-keyed 2025-07-01).
- `marts.dim_date(date_key PK, year, quarter, month, month_name, day_of_week
  1=Mon..7=Sun, day_name, is_weekend, is_holiday, holiday_name, holiday_type,
  is_school_break, is_dining_week, is_marathon_sunday)`.
- `marts.dim_menu_item(menu_item_id PK, item_name, category, standard_price,
  theoretical_unit_cost NULLable)`: 46 items, categories: Brunch & Eggs,
  Starters, Salads & Bowls, Sandwiches & Burgers, Mains, Sides, Desserts,
  NA Beverages, Bar.
- `marts.dim_vendor(vendor_id PK, vendor_name, vendor_category)`: 9 vendors.
- `marts.fact_ticket_line(location_id, business_date, ticket_number,
  line_number, closed_at, daypart[breakfast|lunch|afternoon|dinner|late_night],
  is_brunch, menu_item_id, qty, unit_price, discount_amount,
  line_state[sale|void|comp|refund], order_mode[DI|TO|DL], gross_amount,
  net_amount)`: one deduplicated POS line. net_amount already applies the
  net-sales rule (sales net of discounts, refunds negative, voids/comps zero).
- `marts.fact_invoice_line(invoice_number, line_number, location_id,
  vendor_id, invoice_date, posted_date, item_desc, qty, uom, unit_cost
  NULLable, unit_cost_filled, ext_cost)`: purchases (COGS proxy).
- `marts.fact_labor_day(location_id, business_date, role, hours, wages)`.
- `marts.fact_gl_day(location_id, business_date, gl_net_sales)`.
- `marts.fact_budget_month(location_id, month_start, net_sales_budget,
  cogs_budget, labor_budget)`: rows begin at each location's first full open
  month.

Conventions: money is numeric dollars; "net sales" means sum(net_amount);
"prime cost" means (purchases + wages) / net sales; late-night tickets post to
the prior service date via business_date.
