# Decision memo: Financial District prime cost

**To:** Copperwick leadership team
**From:** Operations Analytics
**Date:** 2026-07-20
**Subject:** Financial District prime cost is 4.20 points over target. Two fixes cover the gap.

## Summary

The Financial District store ran a 64.20% prime cost over the trailing twelve months (July 2025 through June 2026) against the 60.0% target, a miss of 4.20 points (analysis/12). On net sales of $3,017,717, that is $126,878 of annualized excess cost (analysis/12). This is not a blip: the store has been above the 62% alert threshold for 77 consecutive weeks on a rolling 4-week basis, starting the week of January 13, 2025, while no other store has held a streak longer than 7 weeks (analysis/08), and it has missed its monthly target by more than 2 points in all 18 months from January 2025 through June 2026 (analysis/05). Two specific causes explain the gap, and both are correctable.

## What is driving it

Against the store's own 2024 baseline, when it ran 60.20%, prime cost rose 4.00 points. The bridge (analysis/12):

| Line | 2024 baseline | Trailing 12 | Change |
| --- | ---: | ---: | ---: |
| Prime cost, % of net sales | 60.20 | 64.20 | +4.00 |
| Labor, % of net sales | 32.90 | 36.44 | +3.55 |
| Weekend labor, % of weekend sales | 32.86 | 52.91 | +20.05 |
| Weekday labor, % of weekday sales | 32.90 | 33.52 | +0.62 |
| Purchases (COGS proxy), % of net sales | 27.30 | 27.76 | +0.46 |

The weekend and weekday rows carry their own denominators, which is why they do not sum to the
labor line.

**Leg 1: weekend labor outran a flat weekend sales base.** In the trailing twelve months, weekend (Saturday and Sunday) labor ran 52.91% of weekend net sales, up 20.05 points from 32.86% in 2024, while weekday labor barely moved, 33.52% versus 32.90% (analysis/12). The deterioration is concentrated entirely on weekends, and its timing is measurable: the store's run above the 62% alert threshold begins the week of January 13, 2025 (analysis/08). That pattern, a step change in the weekend ratio at the start of 2025 with weekdays untouched, is consistent with the group's weekend schedule template being applied to this store without rescaling to its weekend demand. This leg is 3.55 of the 4.00 points.

**Leg 2: beef price pass-through declined on the two held flagship items.** The beef vendor stepped unit costs up twice, by 6.4 to 6.5% in March 2025 and again by 8.0 to 8.1% in September 2025 across its four beef cuts; hanger steak, for example, moved from $9.20 to $9.80 and then to $10.58 per unit (analysis/10). Other menu items took a price increase during the period, but the two beef flagships, the Copperwick Smash Burger and the Hanger Steak Frites, were held, and this store's mix leans on both. Its purchases as a share of net sales rose 0.44 points from the quarter before the first step to the quarter from the second step, 27.40% to 27.85%, the largest increase among the eight stores open in both windows (analysis/10). That matches the +0.46 point purchases leg in the bridge (analysis/12).

## Recommended actions

1. **Rebuild the weekend schedule template for the Financial District.** This addresses the labor leg, 3.55 of the 4.00 points of drift (analysis/12), which carries most of the $126,878 annualized excess (analysis/12). The store's own 2024 weekend labor ratio of 32.86% of weekend sales (analysis/12) is the working target.
2. **Reprice the two held beef items, the Copperwick Smash Burger and the Hanger Steak Frites.** This addresses the purchases leg, 0.46 points of the drift (analysis/12), created by the vendor's two cost steps of 6.4 to 6.5% and 8.0 to 8.1% (analysis/10) while these two menu prices stood still.

## Caveats and method

Cost here means purchases from vendor invoices. There are no inventory counts, so this is a proxy for consumption, and deliveries are lumpy, so it is only meaningful over windows of 4 or more weeks. That is why the streak analysis uses rolling 4-week prime cost rather than single weeks (analysis/08). The baseline is calendar 2024; the trailing twelve months are July 2025 through June 2026. Dollar and point figures are computed on unrounded values before display, so recomputing from the rounded lines shown here can differ by a cent or a hundredth of a point. Every figure above is transcribed from output of the repository's committed queries, each named inline like (analysis/12).
