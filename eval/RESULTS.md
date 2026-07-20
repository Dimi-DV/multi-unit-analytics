# Text-to-SQL evaluation results

## Results

| Schema condition | Execution match | Rate |
|---|---|---|
| marts (modeled layer) | 23 / 24 | 95.8% |
| raw (all-TEXT layer) | 18 / 24 | 75.0% |

- **Subject model:** claude-sonnet-5.
- **Runner:** claude-cli headless. Each question is answered by a fresh,
  context-free process that sees only the schema context and the question,
  with exactly one answer attempt per question. Transport retries (a network
  error re-sending the same request) are distinct from answer attempts; the
  model never gets a second try at a question.
- **Scoring:** execution match against a canonical result set. Column names
  and column order are ignored, row order is ignored unless the question
  demands ordering, numerics compare with a small tolerance.
- **Run:** bank v2, run 1. The bank was frozen before this run and these are
  the first and only numbers produced against it.

The headline finding is the marts-vs-raw gap on identically contracted
questions: the same 24 questions, with the same output contracts, lose five
additional questions (20.8 points of accuracy) when the model must do the
cleaning (date parsing, dedup, alias resolution, the location re-key) that
the modeled layer already did.

Per-question records: `eval/results/results_marts.json` and
`eval/results/results_raw.json` (gitignored; see "Reproduce it").

## What the gap is made of

Seven failures total: one on marts, six on raw. Auditors executed both the
generated and the canonical query for every failure; verdicts below rest on
those executions, not on reading the SQL.

### Marts: q06, schema linking (1 failure)

The question asks which vendor supplies coffee and tea. The canonical answer
is one row, Quillbrook Coffee Roasters. The generated query searched the
free-text `item_desc` on invoice lines instead of the disclosed
`dim_vendor.vendor_category` attribute, and returned two vendors: `ILIKE
'%tea%'` matches the "tea" inside "Hanger Steak" (1,624 Duncliff Beef &
Provisions invoice lines), while the `'%coffee%'` predicate matched zero rows
(Quillbrook's coffee products are named House Blend Beans and Cold Brew
Concentrate), so Quillbrook itself survived only via "Tea Program". A
category-level probe (`vendor_category ILIKE '%coffee%' OR '%tea%'`) returns
exactly the correct single vendor, and under either reading of the question
(vendor category or actual invoiced items) the true answer is Quillbrook
alone, since Duncliff supplies beef, not tea.

### Raw: refund sign convention flipped (q09, q18, and latent in q08)

All 13,987 refund lines in `raw.pos_ticket_lines` already store `qty = -1`
(refund `discount_amount` is uniformly zero), so a refund's net contribution
`qty * unit_price` is already negative. Three generated queries applied the
"refunds count negative" rule by multiplying refund lines by -1 a second
time, flipping them positive.

- **q09 (average check by location):** every one of the 9 location averages
  is inflated by +0.13 to +0.27 (CW-WV 40.00 vs canonical 39.75, CW-WB 39.39
  vs 39.12, CW-GCX 26.05 vs 25.88, CW-LIC 21.18 vs 21.05, and so on). The
  predicted inflation, 2 x |refund net| / tickets (for CW-WV: 2 x 17,147.50 /
  135,016 = 0.254), matches the observed differences to the rounded cent.
  Removing only the extra -1 makes all 9 rows match the canonical exactly,
  which also proves the query's dedup, date parsing, re-key bridge, and
  include-void/comp/refund-only-ticket denominator were all correct.
- **q18 (days where GL differs from POS):** each double-negated refund shifts
  a day's POS net by twice the refund's gross (on CW-WV 2025-01-02, a single
  -24.00 refund makes the generated POS net 10,741.38 instead of the true
  10,693.38, which ties GL to the penny), so the generated differing-day
  counts land at 76 to 332 per location (CW-WV 332, CW-SOHO 319, CW-UWS 315,
  CW-FD 286, CW-AST 76) against the true zeros everywhere except CW-FD 1 and
  CW-LIC 3. An independent recomputation straight from raw confirms the
  canonical key. Removing only the -1 multiplier reproduces the canonical
  result exactly; dedup, date parsing, CW-GC to CW-GCX bridging, and
  zero-day handling were all correct.
- **q08 (net sales by borough):** the scored failure here is schema linking,
  described below, but the same sign flip sits latent in the query: with the
  broken join repaired it still misses by +123,180.00 Manhattan / +43,433.00
  Brooklyn / +18,919.00 Queens (total +185,532.00), exactly twice the
  92,766.00 of 2025 deduped refunds. Fixing both the join and the sign makes
  the query match the canonical exactly.

An honest caveat toward the instrument: `schema_context_raw.md` states the
net-sales rule ("refunds count negative") but not the feed's stored sign
convention, the same class of undisclosed data fact that bank v1's audit
moved into the schema context for order_mode codes. Refunds counting positive
is not an admissible reading of any wording, and a formulation that gives the
right answer under either sign convention existed, so by this bank's own
precedent these score as model errors, not
ambiguity. The sign convention should still be added to the raw schema
context if it is intended as given rather than discoverable.

### Raw: re-fired line dedup skipped (q13, q16)

The raw schema context states the rule verbatim: rows sharing
(location_code, business_date, ticket_number, line_number) and differing
only in closed_at are re-fired duplicates and must be counted once. Two
generated queries summed straight off `raw.pos_ticket_lines` without
collapsing them.

- **q13 (comp value by location):** 8 of 9 locations agree; CW-WB comes back
  53,012.00 vs canonical 52,893.00, +119.00. Raw contains exactly 8 re-fired
  duplicate comp line groups at CW-WB in November 2025 (each two rows sharing
  the natural key with two distinct closed_at values and identical payloads),
  and their extra copies sum to exactly 119.00.
- **q16 (top 3 items per location, Q4 2025):** 24 of 27 rows agree; the three
  CW-WB rows are inflated (Copperwick Smash Burger 3,776 vs 3,770, Quillbrook
  Drip Coffee 4,419 vs 4,407, Za'atar Fries 3,230 vs 3,222). The Q4 window
  contains 187 duplicate line groups, all at CW-WB, and the extra units from
  those groups (+6, +12, +8) reproduce the deltas exactly. Everything else
  checked out: the line_state filter, the alias join (8 other locations tie
  out to the unit), and the bridge (Q4 is entirely post-re-key). Item
  identities are unchanged; only the unit values differ, so the value match
  rightly fails.

### Raw: q08, schema linking (invented join column)

The generated query returned zero rows because its final join was
`raw.pos_locations.location_code = bridged.location_id`: the bridge's
location_id values are surrogate keys '1' through '9' while pos_locations is
keyed only by codes like 'CW-AST', so the inner join matched nothing. The
schema context lists no location_id column on pos_locations; the linkage was
invented. The canonical (Manhattan 18,811,959.01, Brooklyn 6,418,163.24,
Queens 3,130,692.95) was independently reproduced from raw. The query's
dedup, date parsing, and void/comp handling were correct, and runtime was not
a factor for either query.

### Raw: q22, timeout on semantically correct SQL

The only failure whose SQL is right. Run to completion with no statement
timeout, the generated query returns exactly the canonical result, 2025-05 at
17.00 and 2025-07 at 17.50, identical to full precision, but takes 58.5 to
64.8 seconds against the harness's 20,000 ms limit (canonical: 0.25 s), so it
was killed with QueryCanceled. The cost driver is the re-fired-dedup
ROW_NUMBER() window computed over all 4,847,825 rows of
`raw.pos_ticket_lines`, with per-row regex date parsing and a
regex-plus-replace timestamptz cast inside the window ORDER BY, none of which
the planner can prune with the Kale Caesar filter that sits above the window.
The query also carries a latent alias-join fan-out ('Kale Caesar' and 'KALE
CAESAR' collide under lower(trim), 11,529 matched May lines vs the canonical
5,865), which provably did not affect the answer because unit_price is a
single flat value per month. Runtime was not a factor in any other failure;
the next slowest failing query ran in about 11.6 seconds.

## How this number was produced (and what it is not)

The first full run, against bank v1, scored 7/24 on marts and 5/24 on raw. A
36-failure audit that executed every generated and every canonical query
found that 27 of the 36 failures were semantically correct answers rejected
only because the questions never pinned an output contract: which identifier,
which columns, what rounding, POS or GL as the source of truth. Publishing
those pilot numbers as the headline was rejected because they measure the
questions, not the model, and loosening the scorer was rejected because fuzzy
matching would hide real errors; instead the question wordings were revised
once to state their output contracts exactly, every answer key stayed
untouched (the audit confirmed all 24 correct), and two data-dictionary facts
(order_mode codes, the daypart end-minute convention) moved into the raw
schema context while the discoverable messiness (alias duplicates, re-fired
lines, text typing) stays undocumented on purpose, because finding it is what
the raw condition measures. Because bank v2 was drafted from one model's
pilot failures, it risked fitting the instrument to that model, so all 24
revised questions got an independent blind review against only the question
text, the answer key, and the schema docs, with reviewers barred from the
pilot results; the review closed the remaining contract gaps it found and
retargeted one question whose literal answer was printed in the schema docs,
and two answer keys gained a round() their question already promised, proven
execution-identical before adoption. After that single revision round the
bank was frozen: no further wording changes on the strength of any model's
results. The pilot audit's instrument-adjusted diagnostics, what the pilot
answers would have scored had the contracts been stated, were 22/24 on marts
and 17/24 on raw; the official v2 run landed at 23/24 and 18/24, which
corroborates the audit's finding rather than contradicting it.

What this is not: a general capability claim. It is one model (claude-sonnet-5
inside the Claude Code system prompt via the CLI runner) on one 24-question
bank over one synthetic dataset. The absolute scores are reported as that and
nothing more; the finding this repo stands behind is the within-model gap
between the modeled and raw conditions. The harness also includes an
LLM-as-judge for near-miss analysis, but its human-agreement rate has not
been measured yet, so no judge output is quoted anywhere in this document;
every verdict above comes from executing both queries and comparing results.

## Reproduce it

```
python eval/harness.py --schema marts --runner claude-cli
python eval/harness.py --schema raw --runner claude-cli
```

Fresh runs write to `eval/results/`, which is gitignored: publishing a number
is a deliberate act, not a side effect of running the harness. If a new run
supersedes these numbers, this file is updated by hand, together with its
failure-mode analysis, or not at all.
