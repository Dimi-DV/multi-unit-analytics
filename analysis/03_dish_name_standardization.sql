-- 03 | Dish-name drift standardization
--
-- Business question: what did each dish really sell once drifting POS names
-- (truncations, misspellings, casings, and the fresh batch after the mid-2025
-- POS re-install) are mapped to canonical items, and does anything fall out
-- unmapped?
-- Pattern: conditional / multi-table joins with normalization. The alias map
-- is analyst-maintained reference data; the audit at the bottom is the
-- contract that the map is total. Expected audit result: zero rows.

-- Units by canonical item: as-keyed name count vs canonical rollup
WITH alias_map AS (
    -- distinct on the normalized key: case-only variants must not fan out
    SELECT DISTINCT lower(trim(alias)) AS alias_norm, menu_item_id::smallint AS menu_item_id
    FROM raw.ref_item_aliases
),
keyed AS (
    SELECT
        t.item_name                                   AS as_keyed_name,
        a.menu_item_id,
        sum(t.qty) FILTER (WHERE t.line_state IN ('sale', 'comp')) AS units
    FROM staging.stg_pos__ticket_lines t
    LEFT JOIN alias_map a ON a.alias_norm = lower(trim(t.item_name))
    WHERE t.export_seq = 1
    GROUP BY t.item_name, a.menu_item_id
)
SELECT
    m.item_name                       AS canonical_name,
    count(*)                          AS distinct_keyed_spellings,
    sum(k.units)                      AS total_units,
    sum(k.units) FILTER (WHERE k.as_keyed_name <> m.item_name) AS drifted_units
FROM keyed k
JOIN marts.dim_menu_item m USING (menu_item_id)
GROUP BY m.item_name
HAVING count(*) > 1
ORDER BY drifted_units DESC NULLS LAST;

-- Anti-join audit: raw names with no alias mapping. Contract: zero rows.
SELECT DISTINCT t.item_name
FROM staging.stg_pos__ticket_lines t
LEFT JOIN raw.ref_item_aliases a
       ON lower(trim(a.alias)) = lower(trim(t.item_name))
WHERE a.alias IS NULL;

-- Map-integrity audit: normalized aliases claiming more than one item.
-- Contract: zero rows (case-only variants of one item are fine; the same
-- string mapping to two different items is corrupt reference data).
SELECT lower(trim(alias)) AS alias_norm, count(DISTINCT menu_item_id) AS items
FROM raw.ref_item_aliases
GROUP BY lower(trim(alias))
HAVING count(DISTINCT menu_item_id) > 1;
