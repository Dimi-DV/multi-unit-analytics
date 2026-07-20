# Decisions made (and what was rejected)

Built with Claude Code as a force multiplier: it scaffolded the generator, infra, and this repo's
guardrails, and wrote the SQL layers to the specs and decisions recorded below.

<!-- The entries below were drafted during Phase 0 scaffolding and are pending my edit; each one
     records a real design decision with the alternative that was rejected. -->

- Hybrid seed strategy: commit small dims and a SHA-256 manifest, regenerate the ~400MB of fact
  CSVs at setup. Rejected committing the facts (repo weight, unreviewable diffs) and rejected
  gzip (its embedded mtime header breaks byte-identity, and binary blobs kill diff review).
- No Faker: all names are curated static lists. A generator dependency whose provider data changes
  between versions would hold the byte-identical guarantee hostage.
- All-TEXT raw layer, no constraints: injected mess must never fail a load, and every cast becomes
  an explicit, reviewable cleaning step in staging.
- COGS is purchases (AP invoices), documented as a proxy: no inventory counts exist, so weekly
  prime cost is delivery-lumpy and streak analysis uses rolling 4-week windows instead.
- Menu-mix quadrants are computed within category against the category median: comparing a $4.50
  coffee to a $34 steak on raw margin dollars is price-point bias. Categories with fewer than five
  items fold into their nearest neighbor for quadrant purposes.
- Calendar months, not a 4-4-5 fiscal calendar: the budget and GL stay clean and the weekday-mix
  distortion is acknowledged as a limitation; weekly analyses use ISO weeks.
- No employee dimension: every Phase 1 question resolves at location x day x role grain, and
  synthetic person records add fake-PII smell with zero analytic payoff.
- One economic entity, two POS codes: the mid-2025 format conversion re-keys the store in the POS
  while finance systems never re-key; the bridge seed resolves it. This models the messiest real
  version of a location change without claiming dimensional-modeling-at-scale credentials.
- Grain by post-hook primary key, referential integrity by dbt relationships tests: the PK is the
  thing that must fail the build when dedup breaks, so it stays DDL; foreign keys as constraints
  would force build-order coupling for what tests already prove.
- dbt pinned to what is actually installable (dbt-core 1.12.0, dbt-postgres 1.11.0), not to a
  headline version: this repo must run at clone time months from now.
- Eval numbers ship with failure modes or not at all: the harness makes one attempt per question,
  no retry loop, and the judge is quoted only next to its measured human-agreement rate.
- Eval bank v2 after a measured pilot: the first full run scored 7/24 (marts) and 5/24 (raw), and
  a 36-failure audit that executed every generated and canonical query found 27 failures were
  semantically correct answers rejected only because the questions never pinned an output contract
  (which identifier, which columns, what rounding, POS or GL as the source of truth). Rejected
  publishing the pilot numbers as the headline (they measure the questions, not the model) and
  rejected loosening the scorer (fuzzy column matching would hide real errors). Instead the
  question wordings now state their output contract exactly, every answer key stays untouched
  (the audit confirmed all 24 correct), and the re-run against bank v2 is the official number,
  published together with the pilot story. Two data-dictionary facts (order_mode codes, the
  daypart end-minute convention) moved into the raw schema context; the discoverable messiness
  (alias duplicates, re-fired lines, text typing) stays undocumented on purpose, because finding
  it is what the raw condition measures.
- Blind review before the official run, then freeze: because bank v2 was drafted from a pilot's
  failures, it risks fitting the instrument to one model. Mitigation: an independent review of
  all 24 revised questions against only the question text, the answer key, and the schema docs
  (reviewers were barred from the pilot results) closed the remaining contract gaps it found
  (mostly the business_date vs closed_at window and which code labels the re-keyed store), and
  retargeted one question whose literal answer was printed in the schema docs. Two answer keys
  gained a round() their question already promised, proven execution-identical before adoption.
  After this single revision round the bank is frozen: no further wording changes on the strength
  of any model's results. The headline result is the marts-vs-raw gap within one model on
  identically contracted questions; the absolute score is reported as this model on this bank,
  not as a general capability claim.
