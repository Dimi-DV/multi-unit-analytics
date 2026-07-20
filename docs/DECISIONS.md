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
