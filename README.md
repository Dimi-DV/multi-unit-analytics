# multi-unit-analytics

**Same-store sales, margin variance, and menu-mix analytics on a deliberately messy 9-location POS dataset, in PostgreSQL.**

> The analytical patterns here (same-store growth, margin variance vs. target, product-mix engineering,
> POS-to-ledger reconciliation) are the core of any multi-unit consumer business: retail, franchise,
> QSR, fitness, clinics. The dataset models a fictional 9-location restaurant group because that is the
> domain I ran analytics in professionally for two years; the transactional core is synthetic **by
> design** (real multi-location P&L data is proprietary everywhere), with realism anchored to cited
> public sources. See [Data & methodology](#data--methodology).

Status: dataset, dbt-managed staging/marts layers with 67 passing checks, the twelve analysis
queries, and the text-to-SQL evaluation harness are built and run against the loaded database.
The decision memo, query EXPLAIN notes, and the measured eval accuracy number are in progress;
nothing is claimed here before it exists in this repo.

## The business question

One of nine locations ran 4.2 points over the group's 60.0% prime-cost target for the trailing
twelve months, roughly $127K a year of excess cost (analysis/12). The measured decomposition: a
weekend labor template rolled out group-wide in early 2025 was never rescaled to that store's weak
weekend demand (weekend labor hit 52.9% of weekend sales against a 32.9% baseline), plus a beef
price pass-through the group declined to take on its two beef flagships. Recommended: rebuild the
weekend schedule template and reprice the two held items. Same dataset, same queries also show why
naive growth reads lie: naive H1-2026 growth is +10.2% while true comp growth is +4.8%
(analysis/04), the gap being one opening ramp and one format conversion.

## What's here

| Path | What |
|------|------|
| `generator/` | Seeded, byte-reproducible Python data generator: realistic distributions, a documented parameterized anomaly-injection pass, and a calibration checker that fails if the planted storyline drifts out of tolerance |
| `seeds/` | Committed reference and dimension CSVs, 500-row fact samples, and the SHA-256 manifest that pins the regenerated facts |
| `db/` | Raw-layer DDL: all-TEXT schema-on-read tables (typing is the first transformation) |
| `models/` | dbt project (dbt-core 1.12, Postgres adapter): typed staging views (three date formats, UTC window, dedup ranking) and marts where the cleaning contract is applied exactly once; grain enforced by post-hook primary keys, so the fact build itself is the dedup regression test |
| `tests/` + model YAML | 67 checks: uniqueness, referential relationships, accepted values, a net-sales-rule expression test, and singular tests for tie-out bounds, prime-cost plausibility, and alias-map totality |
| `analysis/` | Twelve numbered business-question queries covering filter+HAVING, conditional joins, top-N per group, LAG/LEAD, gap-and-islands, dedup-keep-latest, and a recursive hierarchy rollup; every headline number above is transcribed from their output |
| `eval/` | Text-to-SQL evaluation harness: 24-question ground-truth bank (answer key validated in CI), execution-match scoring, calibrated-judge protocol. Built and runnable; **no accuracy number is claimed until one is measured** |
| `scripts/` | Loader (psycopg COPY), setup wrappers for PowerShell and make, determinism and content guards |
| `docs/` | [Dataset design and provenance](docs/DATASET.md); the decision memo lands with Phase 1 |

Not jaffle_shop: dbt's canonical tutorial is also a fictional restaurant, so the difference is the
point. This dataset carries multi-location prime cost against budget, a POS-to-GL tie-out, dish-name
drift standardization, a mid-year format conversion with a POS re-key (10 location codes, 9
locations), and a comp-store eligibility rule; a customers-and-orders toy touches none of those.

## Setup

Requires Docker and Python 3.12.

```
git clone <this repo> && cd multi-unit-analytics
./scripts/setup.ps1        # PowerShell; or: make setup
```

That creates a venv with exact pins, regenerates the dataset (about 4 minutes), verifies checksums
against the committed manifest, starts pinned Postgres 16 on port 5433, and loads about 5M rows.
Then `pip install -r requirements-dbt.txt` and `make build` (or `dbt deps && dbt build` with
`DBT_PROFILES_DIR=profiles`) builds every model and runs all 67 checks; any file in `analysis/`
runs with `psql -f`. `python -m generator --verify` re-checks byte-identity at any time.

## Data & methodology

The full design is in [docs/DATASET.md](docs/DATASET.md): the fictional universe, the determinism
contract (fixed seed, single PCG64 stream, integer-cents money, LF discipline, no wall clock), the
ten-item injected-mess catalog with the cleaning step each item maps to, and the planted-findings
policy: findings are planted as generation parameters with tolerance bands enforced by
`python -m generator.calibrate`, and every headline number quoted anywhere is transcribed from
measured query output, never from generator constants.

## Decisions I made (and what I rejected)

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
