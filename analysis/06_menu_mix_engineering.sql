-- 06 | Menu-mix engineering: stars, plowhorses, puzzles, dogs
--
-- Business question: which dishes earn their menu space? Quadrants are
-- computed WITHIN CATEGORY against the category median (comparing a coffee to
-- a steak on raw margin dollars is price-point bias), and separately for the
-- pre and post beef-price eras (2025-09-01 split), because the answer changed.
-- Bar (3 items) folds into NA Beverages for quadrant purposes: a median of
-- three is not a benchmark. The three uncosted rotating items impute their
-- category's median cost ratio, and the imputation is flagged in the output.
-- Note: percentile_cont is an ordered-set aggregate, not a window function in
-- Postgres, so medians come from grouped CTEs joined back on.
-- Pattern: top-N per group (ROW_NUMBER) + grouped aggregates.

-- Quadrant table per era
WITH sold AS (
    SELECT
        m.menu_item_id,
        m.item_name,
        CASE WHEN m.category = 'Bar' THEN 'NA Beverages' ELSE m.category END AS category,
        CASE WHEN f.business_date >= date '2025-09-01' THEN 'post_beef' ELSE 'pre_beef' END AS era,
        m.standard_price,
        m.theoretical_unit_cost,
        (m.theoretical_unit_cost IS NULL) AS cost_imputed,
        sum(f.qty)        AS units
    FROM marts.fact_ticket_line f
    JOIN marts.dim_menu_item m USING (menu_item_id)
    WHERE f.line_state = 'sale'
    GROUP BY 1, 2, 3, 4, 5, 6, 7
),
cost_ratio_median AS (
    SELECT
        category, era,
        percentile_cont(0.5) WITHIN GROUP (
            ORDER BY theoretical_unit_cost / standard_price) AS med_ratio
    FROM sold
    WHERE theoretical_unit_cost IS NOT NULL
    GROUP BY category, era
),
costed AS (
    SELECT
        s.*,
        (s.standard_price
         - COALESCE(s.theoretical_unit_cost, r.med_ratio * s.standard_price)
        ) * s.units AS cm_dollars
    FROM sold s
    JOIN cost_ratio_median r USING (category, era)
),
category_medians AS (
    SELECT
        category, era,
        percentile_cont(0.5) WITHIN GROUP (ORDER BY units)      AS median_units,
        percentile_cont(0.5) WITHIN GROUP (ORDER BY cm_dollars) AS median_cm
    FROM costed
    GROUP BY category, era
)
SELECT
    c.era,
    c.category,
    c.item_name,
    c.units,
    round(c.cm_dollars::numeric, 0) AS cm_dollars,   -- percentile_cont yields float8
    CASE
        WHEN c.units >= g.median_units AND c.cm_dollars >= g.median_cm THEN 'star'
        WHEN c.units >= g.median_units AND c.cm_dollars < g.median_cm  THEN 'plowhorse'
        WHEN c.units < g.median_units AND c.cm_dollars >= g.median_cm  THEN 'puzzle'
        ELSE 'dog'
    END                    AS quadrant,
    c.cost_imputed
FROM costed c
JOIN category_medians g USING (category, era)
ORDER BY c.era, c.category, c.cm_dollars DESC;

-- Top 3 sellers per location per quarter (know the tie behavior: ROW_NUMBER
-- picks one arbitrarily on ties, RANK would admit more than three)
WITH q AS (
    SELECT
        l.location_code,
        d.year,
        d.quarter,
        m.item_name,
        sum(f.qty) AS units,
        row_number() OVER (
            PARTITION BY l.location_code, d.year, d.quarter
            ORDER BY sum(f.qty) DESC, m.item_name
        ) AS rn
    FROM marts.fact_ticket_line f
    JOIN marts.dim_location l USING (location_id)
    JOIN marts.dim_date d ON d.date_key = f.business_date
    JOIN marts.dim_menu_item m USING (menu_item_id)
    WHERE f.line_state = 'sale'
    GROUP BY 1, 2, 3, 4
)
SELECT location_code, year, quarter, rn, item_name, units
FROM q
WHERE rn <= 3
ORDER BY location_code, year, quarter, rn;
