# multi-unit-analytics

[![dataset determinism](https://github.com/Dimi-DV/multi-unit-analytics/actions/workflows/dataset-determinism.yml/badge.svg)](https://github.com/Dimi-DV/multi-unit-analytics/actions/workflows/dataset-determinism.yml)
[![dbt build](https://github.com/Dimi-DV/multi-unit-analytics/actions/workflows/dbt-build.yml/badge.svg)](https://github.com/Dimi-DV/multi-unit-analytics/actions/workflows/dbt-build.yml)

**Same-store sales, margin variance, and menu-mix analytics on a deliberately messy 9-location POS dataset, in PostgreSQL.**

> The analytical patterns here (same-store growth, margin variance vs. target, product-mix engineering,
> POS-to-ledger reconciliation) are the core of any multi-unit consumer business: retail, franchise,
> QSR, fitness, clinics. The dataset models a fictional 9-location restaurant group because that is the
> domain I ran analytics in professionally for two years; the transactional core is synthetic **by
> design** (real multi-location P&L data is proprietary everywhere), with realism anchored to cited
> public sources. See [Data & methodology](#data--methodology).

Status: dataset, dbt-managed staging/marts layers with 67 passing checks, the twelve analysis
queries, the [decision memo](docs/decision-memo.md), [query plan notes](docs/explain-notes.md),
and the text-to-SQL evaluation harness are built and run against the loaded database. The
measured eval accuracy number is in progress; nothing is claimed here before it exists in this repo.

## The business question

One of nine locations ran 4.2 points over the group's 60.0% prime-cost target for the trailing
twelve months, roughly $127K a year of excess cost (analysis/12). The measured decomposition: a
weekend labor template rolled out group-wide in early 2025 was never rescaled to that store's weak
weekend demand (weekend labor hit 52.9% of weekend sales against a 32.9% baseline), plus a beef
price pass-through the group declined to take on its two beef flagships. Recommended: rebuild the
weekend schedule template and reprice the two held items (the full memo:
[docs/decision-memo.md](docs/decision-memo.md)). Same dataset, same queries also show why
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
| `docs/` | [Dataset design and provenance](docs/DATASET.md), [design decisions](docs/DECISIONS.md), the [decision memo](docs/decision-memo.md), and measured [query plan notes](docs/explain-notes.md) |

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

Design decisions and the alternatives that were rejected, along with build tooling notes, are
recorded in [docs/DECISIONS.md](docs/DECISIONS.md).
