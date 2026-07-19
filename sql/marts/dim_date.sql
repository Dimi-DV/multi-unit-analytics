-- marts.dim_date: one row per calendar day, built 1:1 from raw.ref_calendar.
-- DATE-typed primary key on purpose: an integer smart key buys nothing on a
-- single-source Postgres star and costs join readability everywhere.

DROP TABLE IF EXISTS marts.dim_date CASCADE;
CREATE TABLE marts.dim_date (
    date_key           date PRIMARY KEY,
    year               smallint NOT NULL,
    quarter            smallint NOT NULL CHECK (quarter BETWEEN 1 AND 4),
    month              smallint NOT NULL CHECK (month BETWEEN 1 AND 12),
    month_name         text NOT NULL,
    day_of_week        smallint NOT NULL CHECK (day_of_week BETWEEN 1 AND 7),
    day_name           text NOT NULL,
    is_weekend         boolean NOT NULL,
    is_holiday         boolean NOT NULL,
    holiday_name       text,
    holiday_type       text CHECK (holiday_type IN ('federal', 'observance', 'city_event')),
    is_school_break    boolean NOT NULL,
    is_dining_week     boolean NOT NULL,
    is_marathon_sunday boolean NOT NULL
);

INSERT INTO marts.dim_date
SELECT
    date_day::date,
    year::smallint,
    quarter::smallint,
    month::smallint,
    month_name,
    day_of_week::smallint,
    day_name,
    is_weekend::boolean,
    is_holiday::boolean,
    NULLIF(holiday_name, ''),
    NULLIF(holiday_type, ''),
    is_school_break::boolean,
    is_dining_week::boolean,
    is_marathon_sunday::boolean
FROM raw.ref_calendar;
