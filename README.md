# multi-unit-analytics

**Same-store sales, margin variance, and menu-mix analytics on a deliberately messy 9-location POS dataset, in PostgreSQL.**

> The analytical patterns here (same-store growth, margin variance vs. target, product-mix engineering,
> POS-to-ledger reconciliation) are the core of any multi-unit consumer business: retail, franchise,
> QSR, fitness, clinics. The dataset models a fictional 9-location restaurant group because that is the
> domain I ran analytics in professionally for two years; the transactional core is synthetic **by
> design** (real multi-location P&L data is proprietary everywhere), with realism anchored to cited
> public sources. See [Data & methodology](#data--methodology).

Status: Phase 0 (dataset, schema, infrastructure) is built. Phase 1 (the analysis SQL, written by
hand) is in progress; nothing is claimed here before it exists in this repo.

## The business question

<!-- Phase 1: 3-line executive summary: business problem, headline numeric finding, recommended
     action, all transcribed from measured query output. -->

## What's here

| Path | What |
|------|------|
| `generator/` | Seeded, byte-reproducible Python data generator: realistic distributions, a documented parameterized anomaly-injection pass, and a calibration checker that fails if the planted storyline drifts out of tolerance |
| `seeds/` | Committed reference and dimension CSVs, 500-row fact samples, and the SHA-256 manifest that pins the regenerated facts |
| `db/` | Raw-layer DDL: all-TEXT schema-on-read tables (typing is the first transformation) |
| `sql/` | Staging and marts layers; checklist stubs now, hand-written SQL as Phase 1 lands |
| `analysis/` | Twelve numbered business-question queries; spec stubs now, hand-written SQL as Phase 1 lands |
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
`python -m generator --verify` re-checks byte-identity at any time.

## Data & methodology

The full design is in [docs/DATASET.md](docs/DATASET.md): the fictional universe, the determinism
contract (fixed seed, single PCG64 stream, integer-cents money, LF discipline, no wall clock), the
ten-item injected-mess catalog with the cleaning step each item maps to, and the planted-findings
policy: findings are planted as generation parameters with tolerance bands enforced by
`python -m generator.calibrate`, and every headline number quoted anywhere is transcribed from
measured query output, never from generator constants.

## Decisions I made (and what I rejected)

Built with Claude Code as a force multiplier: it scaffolded the generator, infra, and this repo's
guardrails; 

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
