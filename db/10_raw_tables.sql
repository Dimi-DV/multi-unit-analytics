-- Raw layer: schema-on-read. Every column is TEXT, no constraints, no keys.
-- Typing is the first transformation and happens in the staging layer.
-- Column order here is the CSV contract; the generator writes these exact orders.
-- Idempotent: safe to re-run at any time.

CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS marts;

-- POS export: one row per ticket line, dirty grain on purpose.
-- Carries: dish-name drift, re-fired duplicates (same business key, later closed_at),
-- late postings, voids/comps/refunds, mixed date formats, one UTC-styled export window,
-- mis-keyed price outliers, and the mid-2025 location re-code.
DROP TABLE IF EXISTS raw.pos_ticket_lines;
CREATE TABLE raw.pos_ticket_lines (
    location_code   text,
    business_date   text,
    ticket_number   text,
    line_number     text,
    closed_at       text,
    item_name       text,
    qty             text,
    unit_price      text,
    discount_amount text,
    line_state      text,
    order_mode      text
);

-- POS location records: 10 rows for 9 physical locations (one store was re-keyed
-- when its POS was reinstalled during a mid-2025 format conversion).
DROP TABLE IF EXISTS raw.pos_locations;
CREATE TABLE raw.pos_locations (
    location_code  text,
    location_name  text,
    neighborhood   text,
    borough        text,
    service_format text,
    volume_tier    text,
    seats          text,
    open_date      text,
    closed_date    text
);

-- Canonical menu with a few injected category typos and blank costs.
DROP TABLE IF EXISTS raw.pos_menu_items;
CREATE TABLE raw.pos_menu_items (
    menu_item_id          text,
    item_name             text,
    category              text,
    standard_price        text,
    theoretical_unit_cost text
);

-- AP invoice lines: COGS purchases. Carries period-end late postings,
-- NULL unit_cost with ext_cost present, and inconsistent uom strings.
DROP TABLE IF EXISTS raw.ap_invoice_lines;
CREATE TABLE raw.ap_invoice_lines (
    invoice_number text,
    line_number    text,
    location_code  text,
    vendor_name    text,
    invoice_date   text,
    posted_date    text,
    item_desc      text,
    qty            text,
    uom            text,
    unit_cost      text,
    ext_cost       text
);

DROP TABLE IF EXISTS raw.ap_vendors;
CREATE TABLE raw.ap_vendors (
    vendor_id       text,
    vendor_name     text,
    vendor_category text
);

-- Daily labor at location x business date x role grain. Role casing varies.
-- Uses canonical location codes throughout: payroll did not follow the POS re-key.
DROP TABLE IF EXISTS raw.labor_daily;
CREATE TABLE raw.labor_daily (
    business_date text,
    location_code text,
    role          text,
    hours         text,
    wages         text
);

-- GL daily sales: finance's book, canonical location codes throughout.
-- Carries the planted POS-vs-GL reconciliation gap windows.
DROP TABLE IF EXISTS raw.gl_daily_sales;
CREATE TABLE raw.gl_daily_sales (
    business_date text,
    location_code text,
    gl_net_sales  text
);

-- Monthly plan: budget rows begin at each location's first full open month.
DROP TABLE IF EXISTS raw.plan_budget;
CREATE TABLE raw.plan_budget (
    month_start      text,
    location_code    text,
    net_sales_budget text,
    cogs_budget      text,
    labor_budget     text
);

-- Analyst-maintained reference data (the ref_ group).
DROP TABLE IF EXISTS raw.ref_calendar;
CREATE TABLE raw.ref_calendar (
    date_day           text,
    year               text,
    quarter            text,
    month              text,
    month_name         text,
    day_of_week        text,
    day_name           text,
    is_weekend         text,
    is_holiday         text,
    holiday_name       text,
    holiday_type       text,
    is_school_break    text,
    is_dining_week     text,
    is_marathon_sunday text
);

DROP TABLE IF EXISTS raw.ref_dayparts;
CREATE TABLE raw.ref_dayparts (
    daypart    text,
    start_time text,
    end_time   text
);

-- Dish-name alias map, including canonical spellings, so the staging join can be
-- a total inner join with a zero-row anti-join audit (see analysis/03).
DROP TABLE IF EXISTS raw.ref_item_aliases;
CREATE TABLE raw.ref_item_aliases (
    alias        text,
    menu_item_id text
);

-- 10 POS codes -> 9 canonical location ids (the re-key bridge).
DROP TABLE IF EXISTS raw.ref_location_bridge;
CREATE TABLE raw.ref_location_bridge (
    location_code text,
    location_id   text
);
