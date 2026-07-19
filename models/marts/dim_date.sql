-- One row per calendar day, 1:1 from the analyst-maintained calendar seed.
select
    date_day::date                as date_key,
    year::smallint                as year,
    quarter::smallint             as quarter,
    month::smallint               as month,
    month_name,
    day_of_week::smallint         as day_of_week,
    day_name,
    is_weekend::boolean           as is_weekend,
    is_holiday::boolean           as is_holiday,
    nullif(holiday_name, '')      as holiday_name,
    nullif(holiday_type, '')      as holiday_type,
    is_school_break::boolean      as is_school_break,
    is_dining_week::boolean       as is_dining_week,
    is_marathon_sunday::boolean   as is_marathon_sunday
from {{ source('ref', 'calendar') }}
