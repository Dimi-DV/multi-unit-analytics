-- marts.dim_menu_item: one row per canonical menu item (46). NULL theoretical
-- costs are preserved (three rotating items ship without a cost card);
-- imputation happens, documented, in the analysis that needs it.

DROP TABLE IF EXISTS marts.dim_menu_item CASCADE;
CREATE TABLE marts.dim_menu_item (
    menu_item_id          smallint PRIMARY KEY,
    item_name             text NOT NULL UNIQUE,
    category              text NOT NULL CHECK (category IN
        ('Brunch & Eggs', 'Starters', 'Salads & Bowls', 'Sandwiches & Burgers',
         'Mains', 'Sides', 'Desserts', 'NA Beverages', 'Bar')),
    standard_price        numeric(7,2) NOT NULL CHECK (standard_price > 0),
    theoretical_unit_cost numeric(7,4)
);

INSERT INTO marts.dim_menu_item
SELECT menu_item_id, item_name, category, standard_price, theoretical_unit_cost
FROM staging.stg_pos__menu_items;
