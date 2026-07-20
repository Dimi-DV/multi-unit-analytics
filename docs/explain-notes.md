# Query plan notes (EXPLAIN ANALYZE)

These plans were captured with `EXPLAIN (ANALYZE, BUFFERS)` against the loaded local database
(Postgres 16.14, the same local instance the analysis queries run on), executed through psycopg
on the main statement of each file. The point of these notes is plan shape: which nodes PostgreSQL
picked, where the rows collapse, and where the time goes. Exact millisecond timings depend on cache
state and the machine and will differ run to run; the shapes will not. Plans are trimmed to the
informative lines, with `...` marking elided detail. For context measured from these runs:
`marts.fact_ticket_line` returned 4,847,461 rows through the Gather Merge in query 01, and every
full scan of it touched about 60,000 shared 8 kB buffers (roughly 470 MB). The table carries
btree indexes on `(business_date)` and `(menu_item_id)` plus its composite primary key; whether
each plan used them is discussed per query.

## 01_net_sales_foundation.sql: monthly net sales by location

The query aggregates every ticket line into monthly net sales, comp gross, and distinct ticket
counts per location. No filter, full history.

```text
GroupAggregate  (cost=466706.41..1116128.65 rows=324 width=108) (actual time=923.012..1974.683 rows=250 loops=1)
  Group Key: l.location_code, d.year, d.month
  Buffers: shared hit=13350 read=47215, temp read=51336 written=51435
  ->  Gather Merge  (cost=466706.41..1031290.59 rows=4847611 width=55) (actual time=920.726..1521.938 rows=4847461 loops=1)
        Workers Planned: 2
        Workers Launched: 2
        ->  Sort  (cost=465706.38..470755.98 rows=2019838 width=55) (actual time=897.040..993.430 rows=1615820 loops=3)
              Sort Key: l.location_code, d.year, d.month, f.ticket_number
              Sort Method: external merge  Disk: 68728kB
              ...
              ->  Hash Join  (cost=37.72..116095.69 rows=2019838 width=55) (actual time=0.533..431.997 rows=1615820 loops=3)
                    Hash Cond: (f.business_date = d.date_key)
                    ->  Hash Join  (cost=1.20..88286.40 rows=2019838 width=55) (actual time=0.182..294.704 rows=1615820 loops=3)
                          Hash Cond: (f.location_id = l.location_id)
                          ->  Parallel Seq Scan on fact_ticket_line f  (cost=0.00..80486.38 rows=2019838 width=25) (actual time=0.006..109.009 rows=1615820 loops=3)
                          ...
Planning Time: 1.714 ms
Execution Time: 1982.900 ms
```

Walkthrough. There is no WHERE clause, so the query has to read every fact row. A Parallel Seq Scan
(two workers plus the leader, each handling about 1.6M rows) is the correct choice: the
`(business_date)` index is unused because there is no date predicate, and walking an index just to
visit 100 percent of the table would add random I/O on top of the same reads. The two dimension
joins are cheap Hash Joins; dim_location (9 rows) and dim_date (912 rows) fit in kilobyte-sized
hash tables.

The time does not go to the scan (rows start flowing in about 109 ms per worker). It goes to the
Sort. `count(DISTINCT ticket_number)` forces sorted grouped aggregation: PostgreSQL cannot use a
plain HashAggregate here, so each process sorts its share of 4.85M rows on the group key plus
ticket_number, spills to disk (external merge, about 68 MB of temp per process, visible in the
temp read/written buffer counts), and the GroupAggregate then deduplicates ticket numbers per
group as sorted rows stream through Gather Merge. 250 location-months come out.

At 10x volume this is the query that degrades first. The sort spill grows linearly and the query
becomes temp-disk bound. The honest fixes are structural, not index-based: raise work_mem, or
compute distinct tickets at (location, date) grain in a first pass so the expensive DISTINCT runs
on far fewer rows, or persist a daily summary model in dbt.

## 06_menu_mix_engineering.sql: quadrant table per era

The query classifies each menu item as star, plowhorse, puzzle, or dog against its category
medians of units and contribution margin, split into pre and post beef-price eras, with cost
imputation for uncosted items.

```text
Sort  (cost=607343.78..607345.69 rows=761 width=177) (actual time=552.938..556.815 rows=92 loops=1)
  Sort Key: c.era, c.category, c.cm_dollars DESC
  CTE sold
    ->  Finalize GroupAggregate  (cost=565401.54..588236.08 rows=83536 width=135) (actual time=552.457..556.395 rows=92 loops=1)
          ->  Gather Merge  (cost=565401.54..584894.64 rows=167072 width=135) (actual time=552.451..556.362 rows=276 loops=1)
                Workers Planned: 2
                ...
                ->  Partial HashAggregate  (cost=473524.79..551860.40 rows=83536 width=135) (actual time=542.214..542.245 rows=92 loops=3)
                      ->  Hash Join  (cost=2.04..101061.77 rows=1973314 width=131) (actual time=0.301..339.035 rows=1578884 loops=3)
                            Hash Cond: (f.menu_item_id = m.menu_item_id)
                            ->  Parallel Seq Scan on fact_ticket_line f  (cost=0.00..85535.97 rows=1973314 width=10) (actual time=0.149..164.210 rows=1578884 loops=3)
                                  Filter: (line_state = 'sale'::text)
                                  Rows Removed by Filter: 36936
                            ...
  CTE costed
    ->  Hash Join  (cost=14285.70..16700.31 rows=17446 width=143) (actual time=552.694..552.739 rows=92 loops=1)
          ->  GroupAggregate  (cost=12725.65..14076.85 rows=8354 width=72) (actual time=0.161..0.197 rows=16 loops=1)
          ...
  ->  Hash Join  (cost=1909.53..2370.97 rows=761 width=177) (actual time=552.829..552.898 rows=92 loops=1)
        ...
Execution Time: 557.072 ms
```

Walkthrough. All the heavy work happens in one pass inside the `sold` CTE: a Parallel Seq Scan
filters `line_state = 'sale'` (36,936 rows removed per process, about 110,800 total), a Hash Join
attaches the 46-row menu dimension, and a Partial HashAggregate collapses roughly 4.74M sale rows
into 92 item-era groups per process using under 1 MB of memory. Everything after that
(the `percentile_cont` medians, the cost-ratio imputation join, the quadrant join) operates on 92
item rows and 16 category-era median rows; the actual-time stamps show those nodes adding well
under a millisecond on top of the 552 ms the aggregate finishes at.

Neither fact index is used, and correctly so. The `(menu_item_id)` index loses because the join
needs every sale row; hashing a 46-row dimension once beats millions of index probes. The
`(business_date)` index is irrelevant because business_date only feeds the era CASE label, not a
selective predicate. One estimation note: the planner guessed 83,536 groups where 92 exist, and
that inflated estimate echoes through the CTE scans (17,446 estimated vs 92 actual in `costed`).
It is harmless here because the downstream data is tiny either way.

At 10x volume this is the good scaling story: still one scan pass, and the group count is bounded
by menu size times two eras, so aggregate memory stays flat and runtime grows only with the scan.
The file's second statement (top 3 sellers per location-quarter) was measured too: the same scan
and aggregate shape topped by a WindowAgg carrying `Run Condition: (row_number() OVER (?) <= 3)`,
so PostgreSQL stops emitting rows past rank 3 instead of materializing all ranks; 785.775 ms total.

## 08_missed_target_streaks.sql: prime-cost streaks (gap-and-islands)

The query builds weekly sales, purchases, and labor series, computes rolling 4-week prime cost per
location, flags weeks over 62 percent, and finds consecutive-week streaks of at least 4 via the
row_number difference trick.

```text
Sort  (cost=120647.61..120647.62 rows=2 width=56) (actual time=687.037..689.697 rows=2 loops=1)
  ->  GroupAggregate  (cost=120647.46..120647.60 rows=2 width=56) (actual time=687.026..689.692 rows=2 loops=1)
        Filter: (count(*) >= 4)
        ...
        ->  Hash Join  (cost=118831.03..120647.41 rows=5 width=44) (actual time=686.985..689.665 rows=84 loops=1)
              ->  WindowAgg  (cost=118829.82..120646.13 rows=5 width=15) (actual time=686.958..689.629 rows=84 loops=1)
                    ...
                    ->  WindowAgg  (cost=118375.83..120645.75 rows=5 width=15) (actual time=686.826..689.595 rows=84 loops=1)
                          ...
                          ->  Subquery Scan on rolled  (cost=117808.43..120645.38 rows=5 width=7) (actual time=685.728..689.548 rows=84 loops=1)
                                Filter: ((rolled.net_4w > '0'::numeric) AND (rolled.weeks_in_window = 4) AND (((100.0 * (rolled.cogs_4w + rolled.labor_4w)) / rolled.net_4w) > 62.0))
                                Rows Removed by Filter: 1006
                                ->  WindowAgg  (cost=117808.43..120441.03 rows=8172 width=110) (actual time=684.294..689.192 rows=1090 loops=1)
                                      ->  Merge Left Join  (cost=117808.43..120236.73 rows=8172 width=102) (actual time=684.275..688.337 rows=1090 loops=1)
                                            ->  Merge Left Join  (cost=115706.48..118045.90 rows=8172 width=70) (actual time=665.003..668.878 rows=1090 loops=1)
                                                  ->  Finalize GroupAggregate  (cost=112478.45..114712.26 rows=8172 width=38) (actual time=639.409..643.050 rows=1090 loops=1)
                                                        ...
                                                        ->  Partial HashAggregate  (cost=110783.95..110947.39 rows=8172 width=38) (actual time=629.411..629.601 rows=947 loops=3)
                                                              ->  Parallel Seq Scan on fact_ticket_line  (cost=0.00..95635.16 rows=2019838 width=11) (actual time=0.160..469.568 rows=1615820 loops=3)
                                                  ...
                                                  ->  Seq Scan on fact_invoice_line  (cost=0.00..2083.60 rows=67863 width=12) (actual time=0.020..18.336 rows=67863 loops=1)
                                            ...
                                            ->  Seq Scan on fact_labor_day  (cost=0.00..1264.39 rows=50308 width=12) (actual time=0.014..13.446 rows=50308 loops=1)
Planning Time: 1.477 ms
Execution Time: 690.055 ms
```

Walkthrough. The plan is a funnel. Three grain-reduction aggregates run first: 4.85M ticket lines
collapse to 1,090 location-weeks (parallel seq scan plus hash aggregate), 67,863 invoice lines and
50,308 labor days collapse to the same weekly grain, and two Merge Left Joins align the three
series. From there the entire gap-and-islands apparatus (the rolling 4-week WindowAgg, the filter
that keeps 84 over-threshold weeks and removes 1,006, the two row_number WindowAggs with their
Incremental Sorts, and the final HAVING that leaves 2 streaks) runs on at most 1,090 rows and is
noise in the runtime. The 690 ms total is essentially the ticket-line scan and aggregate, which
alone accounts for about 643 ms of it.

No fact index is used, and none should be: each CTE is a full-history rollup with no predicate,
and the grouping key is the expression `date_trunc('week', business_date)`, which the plain
`(business_date)` btree cannot serve as a grouping index. One thing worth noticing: at the
`rolled` filter the planner estimates 5 rows where 84 arrive. Everything behind a window function
is a guess to the planner, since it cannot see through WindowAgg output. Here that misestimate is
free because the downstream nodes are tiny, but in a bigger query a 17x under-estimate feeding a
join could pick a bad nested loop.

At 10x ticket volume only the scan side grows. The weekly grain is fixed by calendar length and
location count, so the islands logic would process the same 1,090 rows regardless. Persisting the
weekly rollup as a dbt model would remove nearly all of this query's cost; the streak detection
itself is already effectively free.
