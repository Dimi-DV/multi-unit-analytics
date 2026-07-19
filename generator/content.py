"""Curated static content: the fictional Copperwick universe.

Everything in this file is invented. No external data dependency (no Faker):
byte-identical output must never depend on a third-party provider dataset.
All money values are integer cents. All weights are plain ints/floats consumed
in a fixed order by the generator.
"""

from dataclasses import dataclass, field
from datetime import date

# ---------------------------------------------------------------- categories

CAT_BRUNCH = "Brunch & Eggs"
CAT_STARTERS = "Starters"
CAT_SALADS = "Salads & Bowls"
CAT_SAND = "Sandwiches & Burgers"
CAT_MAINS = "Mains"
CAT_SIDES = "Sides"
CAT_DESSERTS = "Desserts"
CAT_NABEV = "NA Beverages"
CAT_BAR = "Bar"

# Fixed category order: index positions are part of the deterministic draw order.
CATEGORIES = [CAT_BRUNCH, CAT_STARTERS, CAT_SALADS, CAT_SAND, CAT_MAINS,
              CAT_SIDES, CAT_DESSERTS, CAT_NABEV, CAT_BAR]

# Cost-composition keys map 1:1 to vendors (see VENDORS below).
COST_KEYS = ["beef", "poultry", "seafood", "produce", "dairy", "dry",
             "coffee", "na_bev", "bar", "packaging"]

# ---------------------------------------------------------------- menu

POPULARITY_WEIGHT = {"VH": 8.0, "H": 5.0, "M": 2.5, "L": 1.0}


@dataclass(frozen=True)
class MenuItem:
    item_id: int
    name: str
    category: str
    price_cents: int          # 2024 menu price
    fc_bp: int                # target food cost, basis points of price (2024 card)
    tier: str                 # VH / H / M / L popularity
    split: dict               # cost composition over COST_KEYS (sums to 1.0)
    held_at_round: bool = False   # excluded from the 2025-06-15 +3% price round
    seasonal_months: tuple = ()   # if set, only sold in these months


MENU: list[MenuItem] = [
    MenuItem(1, "Buttermilk Stack", CAT_BRUNCH, 1700, 1600, "H", {"dry": .50, "dairy": .35, "produce": .15}),
    MenuItem(2, "Copperwick Breakfast", CAT_BRUNCH, 1600, 2400, "H", {"dairy": .30, "beef": .25, "produce": .20, "dry": .25}),
    MenuItem(3, "Shakshuka Skillet", CAT_BRUNCH, 1900, 2200, "M", {"produce": .45, "dairy": .35, "dry": .20}),
    MenuItem(4, "Brioche French Toast", CAT_BRUNCH, 1800, 1800, "M", {"dry": .45, "dairy": .45, "produce": .10}),
    MenuItem(5, "Short Rib Hash", CAT_BRUNCH, 2100, 2700, "M", {"beef": .55, "produce": .25, "dairy": .20}),
    MenuItem(6, "Green Goddess Omelette", CAT_BRUNCH, 1800, 2000, "L", {"dairy": .50, "produce": .40, "dry": .10}),
    MenuItem(7, "Avocado Toast", CAT_BRUNCH, 1600, 2600, "H", {"produce": .70, "dry": .30}),
    MenuItem(8, "Crispy Brussels & Hot Honey", CAT_STARTERS, 1400, 2000, "H", {"produce": .80, "dry": .20}),
    MenuItem(9, "Za'atar Fries", CAT_STARTERS, 1100, 1800, "VH", {"produce": .60, "dry": .40}),
    MenuItem(10, "Deviled Eggs & Dukkah", CAT_STARTERS, 1200, 1500, "M", {"dairy": .60, "dry": .40}),
    MenuItem(11, "Smoked Trout Dip", CAT_STARTERS, 1600, 2700, "L", {"seafood": .70, "dairy": .15, "dry": .15}),
    MenuItem(12, "Chili-Maple Wings", CAT_STARTERS, 1700, 3400, "H", {"poultry": .75, "dry": .25}),
    MenuItem(13, "Cornbread Skillet", CAT_STARTERS, 900, 1700, "M", {"dry": .70, "dairy": .30}),
    MenuItem(14, "Kale Caesar", CAT_SALADS, 1700, 2100, "H", {"produce": .60, "dairy": .25, "dry": .15}),
    MenuItem(15, "Chopped Farm Salad", CAT_SALADS, 1600, 2300, "M", {"produce": .75, "dairy": .15, "dry": .10}),
    MenuItem(16, "Harvest Grain Bowl", CAT_SALADS, 1800, 3400, "L", {"produce": .55, "dry": .45}),
    MenuItem(17, "Charred Broccoli Bowl", CAT_SALADS, 1700, 2500, "L", {"produce": .70, "dry": .30}),
    MenuItem(18, "Steak & Greens Salad", CAT_SALADS, 2400, 3300, "M", {"beef": .50, "produce": .40, "dry": .10}),
    MenuItem(19, "Copperwick Smash Burger", CAT_SAND, 1900, 3000, "VH", {"beef": .60, "dairy": .10, "produce": .10, "dry": .20}, held_at_round=True),
    MenuItem(20, "Crispy Chicken Sandwich", CAT_SAND, 1800, 2800, "H", {"poultry": .60, "produce": .15, "dry": .25}),
    MenuItem(21, "Turkey Club on Sourdough", CAT_SAND, 1700, 2900, "M", {"poultry": .55, "beef": .15, "produce": .15, "dry": .15}),
    MenuItem(22, "Mushroom Reuben", CAT_SAND, 1600, 2400, "L", {"produce": .55, "dairy": .20, "dry": .25}),
    MenuItem(23, "BLT&E", CAT_SAND, 1500, 2600, "M", {"beef": .45, "produce": .30, "dry": .25}),
    MenuItem(24, "Short Rib French Dip", CAT_SAND, 2200, 3200, "M", {"beef": .55, "dry": .30, "dairy": .15}),
    MenuItem(25, "Harissa Half Chicken", CAT_MAINS, 2800, 2400, "L", {"poultry": .70, "produce": .20, "dry": .10}),
    MenuItem(26, "Hanger Steak Frites", CAT_MAINS, 3400, 3400, "M", {"beef": .75, "produce": .15, "dry": .10}, held_at_round=True),
    MenuItem(27, "Smoked Short Rib Plate", CAT_MAINS, 3300, 3300, "L", {"beef": .70, "produce": .20, "dry": .10}),
    MenuItem(28, "Roasted Salmon, Charred Lemon", CAT_MAINS, 2900, 3100, "M", {"seafood": .75, "produce": .20, "dry": .05}),
    MenuItem(29, "Fish & Chips", CAT_MAINS, 2400, 2900, "M", {"seafood": .60, "produce": .25, "dry": .15}),
    MenuItem(30, "Chicken Pot Pie", CAT_MAINS, 2300, 2200, "M", {"poultry": .50, "dairy": .20, "produce": .15, "dry": .15}),
    MenuItem(31, "Mac & Greens", CAT_MAINS, 1800, 1900, "H", {"dairy": .50, "dry": .35, "produce": .15}),
    MenuItem(32, "Skillet Potatoes", CAT_SIDES, 800, 1400, "H", {"produce": .80, "dry": .20}),
    MenuItem(33, "Street Corn", CAT_SIDES, 900, 2000, "M", {"produce": .85, "dairy": .15}, seasonal_months=(6, 7, 8, 9)),
    MenuItem(34, "Garlicky Green Beans", CAT_SIDES, 900, 1800, "L", {"produce": .85, "dry": .15}),
    MenuItem(35, "Sourdough & Cultured Butter", CAT_SIDES, 500, 2200, "M", {"dry": .60, "dairy": .40}),
    MenuItem(36, "Salted Honey Pie", CAT_DESSERTS, 1100, 1600, "M", {"dry": .60, "dairy": .40}),
    MenuItem(37, "Warm Chocolate Pudding Cake", CAT_DESSERTS, 1200, 1800, "M", {"dry": .70, "dairy": .30}),
    MenuItem(38, "Soft-Serve Sundae", CAT_DESSERTS, 900, 1200, "H", {"dairy": .80, "dry": .20}),
    MenuItem(39, "Seasonal Fruit Crisp", CAT_DESSERTS, 1100, 2100, "L", {"produce": .60, "dry": .30, "dairy": .10}),
    MenuItem(40, "Quillbrook Drip Coffee", CAT_NABEV, 450, 800, "VH", {"coffee": 1.0}),
    MenuItem(41, "Iced Maple Latte", CAT_NABEV, 700, 1200, "H", {"coffee": .60, "dairy": .30, "dry": .10}),
    MenuItem(42, "Fresh Lemonade", CAT_NABEV, 600, 1000, "H", {"produce": .60, "na_bev": .40}),
    MenuItem(43, "House-Brewed Iced Tea", CAT_NABEV, 500, 600, "M", {"coffee": .70, "na_bev": .30}),
    MenuItem(44, "Draft Lager", CAT_BAR, 900, 2200, "H", {"bar": 1.0}),
    MenuItem(45, "House Wine (glass)", CAT_BAR, 1300, 2800, "M", {"bar": 1.0}),
    MenuItem(46, "Garden Gimlet", CAT_BAR, 1500, 1700, "M", {"bar": 1.0}),
]

# Rotating/seasonal items carried without a cost card in the POS export
# (menu CSV renders a blank theoretical_unit_cost; internal cost still exists
# so purchase demand stays correct). Messiness item 6, menu side.
UNCOSTED_MENU_IDS = (33, 38, 39)

# Items with a typo'd/miscased category string in the committed menu CSV
# (messiness item 8, menu side). id -> raw category string as exported.
MENU_CATEGORY_TYPOS = {
    11: "Starters ",
    22: "sandwiches & burgers",
    34: "SIDES",
}

# Express (counter-service) menu subset: no bar, no plated mains service.
EXPRESS_ITEM_IDS = frozenset({1, 2, 7, 9, 14, 15, 16, 17, 19, 20, 21, 23,
                              31, 32, 35, 36, 37, 38, 40, 41, 42, 43})

# ------------------------------------------------------- dish-name drift

# Single source of truth for messiness item 1: the generator draws emitted
# variants from these lists, and the committed ref_item_aliases seed is built
# from these same lists plus every canonical name. item_id -> variants.
DRIFT_VARIANTS: dict[int, tuple[str, ...]] = {
    19: ("Smash Burger", "SMASHBURGER", "Cpwk Smash Brgr"),
    14: ("Kale Ceasar", "KALE CAESAR", "Ceasar-Kale"),
    3: ("Shakshouka", "Shak Shuka Skillet", "SHAKSHUKA"),
    7: ("Avo Toast", "avacado toast", "AVOCADO TST"),
    9: ("Zaatar Fries", "Za atar Fries", "ZATAR FRY"),
    25: ("Harrisa Chicken", "Har. 1/2 Chicken", "HARISSA CHIX"),
    4: ("Frnch Toast", "FR TOAST", "French Tst Brioche"),
    1: ("B-Milk Stack", "Buttermlk Pancakes", "PANCAKE STACK"),
}

# Extra variants introduced by the Grand Central POS re-install (2025-07-01):
# a re-keyed POS means re-typed buttons. Only emitted by CW-GCX.
DRIFT_VARIANTS_GCX: dict[int, tuple[str, ...]] = {
    19: ("Smash Brgr GCX", "SMASH BURGER."),
    14: ("Kale Caesar Sm", "KALE CSR"),
}

# ---------------------------------------------------------------- vendors

@dataclass(frozen=True)
class Vendor:
    vendor_id: int
    name: str
    category: str            # one of COST_KEYS
    prefix: str               # invoice number prefix
    delivery_weekdays: tuple  # ISO weekday numbers (1=Mon .. 7=Sun)


VENDORS: list[Vendor] = [
    Vendor(1, "Duncliff Beef & Provisions", "beef", "DBP", (2, 5)),
    Vendor(2, "Duncliff Beef & Provisions", "poultry", "DBP", (2, 5)),   # same house, poultry book
    Vendor(3, "Windrow Fish Co.", "seafood", "WFC", (2, 4)),
    Vendor(4, "Hudson Crate Produce", "produce", "HCP", (1, 3, 6)),
    Vendor(5, "Kettleboro Dairy & Eggs", "dairy", "KDE", (1, 4)),
    Vendor(6, "Granary Hill Dry Goods", "dry", "GHD", (3,)),
    Vendor(7, "Quillbrook Coffee Roasters", "coffee", "QCR", (2,)),
    Vendor(8, "Meridian Beverage Supply", "na_bev", "MBS", (1,)),
    Vendor(9, "Harborline Wine & Spirits", "bar", "HWS", (4,)),
    Vendor(10, "Cleanline Paper & Packaging", "packaging", "CPP", (3,)),
]

# The committed ap_vendors seed has one row per house (9 rows): the two Duncliff
# cost books share a vendor_id in the seed. vendor_id here is internal.
VENDOR_SEED_ROWS = [
    ("1", "Duncliff Beef & Provisions", "protein"),
    ("2", "Windrow Fish Co.", "seafood"),
    ("3", "Hudson Crate Produce", "produce"),
    ("4", "Kettleboro Dairy & Eggs", "dairy_eggs"),
    ("5", "Granary Hill Dry Goods", "dry_goods"),
    ("6", "Quillbrook Coffee Roasters", "coffee_tea"),
    ("7", "Meridian Beverage Supply", "na_beverage"),
    ("8", "Harborline Wine & Spirits", "bar"),
    ("9", "Cleanline Paper & Packaging", "packaging"),
]

# Catalog per cost key: (item_desc, uom, base unit cost cents, weight, is_beef_line)
VENDOR_CATALOG: dict[str, list[tuple]] = {
    "beef": [
        ("Ground Beef 80/20", "LB", 385, 5.0, True),
        ("Beef Short Rib", "LB", 690, 3.0, True),
        ("Hanger Steak", "LB", 920, 2.0, True),
        ("Brisket", "LB", 560, 1.5, True),
        ("Pork Belly", "LB", 410, 1.0, False),
        ("Applewood Bacon", "LB", 460, 2.5, False),
    ],
    "poultry": [
        ("Half Chickens", "EA", 390, 3.0, False),
        ("Chicken Breast", "LB", 330, 3.0, False),
        ("Party Wings", "LB", 315, 2.0, False),
        ("Ground Turkey", "LB", 345, 1.0, False),
    ],
    "seafood": [
        ("Salmon Fillet", "LB", 890, 3.0, False),
        ("Cod Loin", "LB", 710, 2.0, False),
        ("Smoked Trout", "LB", 1150, 1.0, False),
    ],
    "produce": [
        ("Avocados 48ct", "CS", 5800, 2.0, False),
        ("Lacinato Kale", "CS", 2400, 2.0, False),
        ("Mixed Greens", "CS", 2100, 2.0, False),
        ("Tomatoes 25lb", "CS", 2900, 1.5, False),
        ("Potatoes 50lb", "BG", 2700, 2.5, False),
        ("Lemons 115ct", "CS", 3300, 1.5, False),
        ("Brussels Sprouts", "LB", 240, 1.5, False),
        ("Yellow Onions 50lb", "BG", 1900, 1.5, False),
        ("Herb Mix", "CS", 2600, 1.0, False),
    ],
    "dairy": [
        ("Eggs 15dz Loose", "CS", 4200, 3.0, False),
        ("Butter Solids 36lb", "CS", 11800, 2.0, False),
        ("Whole Milk", "GAL", 390, 2.0, False),
        ("Cheddar Block", "LB", 310, 2.0, False),
        ("Heavy Cream", "QT", 320, 1.5, False),
        ("Soft-Serve Base", "CS", 4600, 1.0, False),
    ],
    "dry": [
        ("AP Flour 50lb", "BG", 2100, 2.0, False),
        ("Cane Sugar 50lb", "BG", 2400, 1.5, False),
        ("Carolina Rice 50lb", "BG", 2800, 1.0, False),
        ("Fry Oil 35lb JIB", "EA", 3800, 2.5, False),
        ("Spice Program", "CS", 4400, 1.0, False),
        ("Potato Buns 96ct", "CS", 3100, 2.0, False),
        ("Maple Syrup", "GAL", 5200, 1.0, False),
        ("Baking Chocolate", "CS", 6300, 1.0, False),
    ],
    "coffee": [
        ("House Blend Beans", "LB", 975, 3.0, False),
        ("Cold Brew Concentrate", "GAL", 2100, 1.5, False),
        ("Tea Program", "CS", 3400, 1.0, False),
    ],
    "na_bev": [
        ("Lemonade Base", "CS", 2700, 2.0, False),
        ("House Syrups", "CS", 3100, 1.5, False),
        ("Sparkling Water 24ct", "CS", 2200, 1.0, False),
    ],
    "bar": [
        ("Local Lager 1/2 BBL", "KEG", 19500, 2.0, False),
        ("House Wine 12ct", "CS", 9600, 2.0, False),
        ("Gin 6ct", "CS", 21000, 1.0, False),
        ("Bar Mixers", "CS", 2500, 1.5, False),
    ],
    "packaging": [
        ("To-Go Containers", "CS", 6400, 2.5, False),
        ("Hot/Cold Cups", "CS", 5100, 2.0, False),
        ("Napkins & Rollups", "CS", 2900, 1.0, False),
        ("Carry Bags", "CS", 3300, 1.5, False),
    ],
}

# ---------------------------------------------------------------- locations

@dataclass(frozen=True)
class Era:
    """One attribute era of a location. Full-window locations have one era."""
    code: str
    service_format: str        # full_service | counter_service
    volume_tier: str           # T1..T4
    seats: int
    valid_from: date
    valid_to: date | None      # None = through end of window
    base_weekday_tickets: float
    weekend_mult: float
    avg_food_lines: float      # mean food lines per ticket (Poisson lam + 1)
    ticket_seq_start: int
    labor_pct: float           # planned labor as share of expected net sales
    daypart_w_wd: dict         # weekday daypart weights
    daypart_w_we: dict         # weekend daypart weights
    na_attach: float           # P(ticket gets an NA beverage line)
    bar_attach: float          # P(dinner/late ticket gets a bar line)
    order_mode_p: tuple        # (DI, TO, DL)
    item_bias: dict = field(default_factory=dict)   # item_id -> weight mult


@dataclass(frozen=True)
class Location:
    location_id: int
    name: str
    neighborhood: str
    borough: str
    open_date: date
    eras: tuple      # 1 or 2 Era entries, chronological
    month_seas_overrides: dict = field(default_factory=dict)  # month -> mult


DP_FULL_WD = {"breakfast": 8, "lunch": 27, "afternoon": 9, "dinner": 42, "late_night": 14}
DP_FULL_WE = {"breakfast": 6, "lunch": 40, "afternoon": 12, "dinner": 34, "late_night": 8}   # weekend lunch block = brunch
DP_OFFICE_WD = {"breakfast": 14, "lunch": 52, "afternoon": 10, "dinner": 20, "late_night": 4}
DP_OFFICE_WE = {"breakfast": 10, "lunch": 55, "afternoon": 15, "dinner": 20, "late_night": 0}
DP_EXPRESS_WD = {"breakfast": 22, "lunch": 56, "afternoon": 12, "dinner": 10, "late_night": 0}
DP_EXPRESS_WE = {"breakfast": 25, "lunch": 55, "afternoon": 12, "dinner": 8, "late_night": 0}
DP_LATE_WD = {"breakfast": 4, "lunch": 20, "afternoon": 8, "dinner": 44, "late_night": 24}
DP_LATE_WE = {"breakfast": 3, "lunch": 34, "afternoon": 10, "dinner": 33, "late_night": 20}

D0 = date(2024, 1, 1)

LOCATIONS: list[Location] = [
    Location(1, "Copperwick West Village", "West Village", "Manhattan", date(2016, 5, 12),
             eras=(Era("CW-WV", "full_service", "T1", 110, D0, None, 310, 1.55, 1.95, 210_000,
                       0.315, DP_FULL_WD, DP_FULL_WE, 0.58, 0.32, (0.78, 0.15, 0.07)),),
             month_seas_overrides={12: 1.18}),
    Location(2, "Copperwick Upper West Side", "Upper West Side", "Manhattan", date(2017, 10, 3),
             eras=(Era("CW-UWS", "full_service", "T2", 95, D0, None, 235, 1.50, 1.90, 220_000,
                       0.323, DP_FULL_WD, DP_FULL_WE, 0.55, 0.22, (0.80, 0.14, 0.06)),)),
    Location(3, "Copperwick Grand Central", "Grand Central", "Manhattan", date(2018, 3, 20),
             eras=(Era("CW-GC", "full_service", "T2", 85, D0, date(2025, 6, 30), 354, 0.35, 1.75, 230_000,
                       0.325, DP_OFFICE_WD, DP_OFFICE_WE, 0.44, 0.18, (0.62, 0.30, 0.08)),
                   Era("CW-GCX", "counter_service", "T3", 48, date(2025, 7, 1), None, 424, 0.30, 1.05, 5_000_000,
                       0.265, DP_EXPRESS_WD, DP_EXPRESS_WE, 0.44, 0.0, (0.34, 0.52, 0.14)))),
    Location(4, "Copperwick SoHo", "SoHo", "Manhattan", date(2019, 6, 11),
             eras=(Era("CW-SOHO", "full_service", "T2", 75, D0, None, 239, 1.25, 1.90, 240_000,
                       0.320, {"breakfast": 7, "lunch": 30, "afternoon": 18, "dinner": 36, "late_night": 9},
                       {"breakfast": 5, "lunch": 38, "afternoon": 20, "dinner": 30, "late_night": 7},
                       0.56, 0.28, (0.76, 0.17, 0.07)),),
             month_seas_overrides={12: 1.22, 7: 1.05, 8: 1.02}),
    Location(5, "Copperwick Financial District", "Financial District", "Manhattan", date(2019, 11, 5),
             eras=(Era("CW-FD", "full_service", "T3", 70, D0, None, 266, 0.45, 1.85, 250_000,
                       0.329, DP_OFFICE_WD, DP_OFFICE_WE, 0.43, 0.35, (0.70, 0.22, 0.08),
                       item_bias={19: 2.3, 26: 1.8, 24: 1.7, 5: 1.3}),),
             month_seas_overrides={8: 0.80, 7: 0.88}),
    Location(6, "Copperwick Williamsburg", "Williamsburg", "Brooklyn", date(2021, 4, 16),
             eras=(Era("CW-WB", "full_service", "T2", 80, D0, None, 211, 1.45, 1.90, 260_000,
                       0.318, DP_LATE_WD, DP_LATE_WE, 0.50, 0.40, (0.74, 0.17, 0.09)),)),
    Location(7, "Copperwick Park Slope", "Park Slope", "Brooklyn", date(2022, 8, 9),
             eras=(Era("CW-PS", "full_service", "T3", 65, D0, None, 193, 1.50, 1.90, 270_000,
                       0.327, DP_FULL_WD, DP_FULL_WE, 0.57, 0.20, (0.78, 0.16, 0.06)),),
             month_seas_overrides={1: 0.84}),
    Location(8, "Copperwick LIC Express", "Long Island City", "Queens", date(2023, 2, 21),
             eras=(Era("CW-LIC", "counter_service", "T4", 35, D0, None, 326, 0.60, 1.10, 280_000,
                       0.262, DP_EXPRESS_WD, DP_EXPRESS_WE, 0.60, 0.0, (0.30, 0.50, 0.20)),)),
    Location(9, "Copperwick Astoria", "Astoria", "Queens", date(2025, 9, 16),
             eras=(Era("CW-AST", "full_service", "T3", 70, date(2025, 9, 16), None, 183, 1.40, 1.90, 290_000,
                       0.330, DP_FULL_WD, DP_FULL_WE, 0.54, 0.26, (0.77, 0.16, 0.07)),)),
]

ITEM_BY_ID = {m.item_id: m for m in MENU}

# Group-level month seasonality (multiplier on expected tickets).
MONTH_SEASONALITY = {1: 0.88, 2: 0.92, 3: 0.98, 4: 1.00, 5: 1.04, 6: 1.02,
                     7: 0.97, 8: 0.93, 9: 1.00, 10: 1.04, 11: 1.03, 12: 1.12}

# Nominal traffic growth by calendar year (price growth comes from the menu round).
YEAR_TRAFFIC = {2024: 1.000, 2025: 1.015, 2026: 1.035}

# Role sets by format: counter-service stores carry no servers/bussers/bartenders.
# (rate cents/hour is a blended fully-loaded employer cost, documented in DATASET.md)
ROLES_FULL = ("manager", "line_cook", "prep_cook", "server", "busser", "bartender", "dishwasher")
ROLES_COUNTER = ("manager", "line_cook", "prep_cook", "counter", "dishwasher")
ROLE_SHARE_FULL = {"manager": .13, "line_cook": .27, "prep_cook": .12, "server": .26,
                   "busser": .07, "bartender": .08, "dishwasher": .07}
ROLE_SHARE_COUNTER = {"manager": .16, "line_cook": .34, "prep_cook": .16, "counter": .22, "dishwasher": .12}
ROLE_RATE = {  # cents per hour, fully loaded; +4% from 2026-01-01 (NYC wage floor step)
    "manager": 3300, "line_cook": 2450, "prep_cook": 2150, "server": 1750,
    "busser": 1700, "bartender": 2000, "counter": 1850, "dishwasher": 1700,
}
ROLE_RATE_2026_MULT = 1.04

# Category weights by daypart (columns follow CATEGORIES order).
#                 BRU  STA  SAL  SAN  MAI  SID  DES  (NA Bev and Bar via attach)
CAT_W = {
    "breakfast":  (62, 4, 6, 16, 0, 8, 4),
    "lunch":      (6, 12, 20, 34, 12, 10, 6),
    "afternoon":  (6, 24, 10, 22, 4, 10, 24),
    "dinner":     (0, 22, 9, 14, 34, 12, 9),
    "late_night": (2, 30, 4, 34, 8, 10, 12),
    "brunch":     (48, 8, 10, 16, 4, 8, 6),   # weekend 10:00-15:00 flag window
}
