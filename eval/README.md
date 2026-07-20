# Text-to-SQL evaluation harness

Measurement, not a chatbot demo. This harness asks a pinned LLM to answer
natural-language business questions against this repo's marts schema, executes
the generated SQL read-only, and scores it by **execution match** against a
canonical result set. An LLM-as-judge is the secondary scorer and is itself
calibrated: a sampled subset gets hand-scored, and the judge's human-agreement
rate is reported next to anything the judge says.

## Status

The harness, question bank, and scorers are complete and runnable. **No
accuracy number is claimed anywhere in this repo yet** because none has been
measured (the run requires an `ANTHROPIC_API_KEY`, and the judge calibration
requires hand-scoring). The number gets published here together with its
failure-mode analysis, or not at all.

## Design

- `bank.yaml`: natural-language questions with canonical SQL, difficulty tags,
  and a match mode. Multiple SQL formulations are expected; only the result
  set matters.
- `harness.py`: schema context from `schema_context.md`, one attempt per
  question (no retries, no error-message feedback loops: the measured number
  should not hide a self-repair budget), read-only execution with
  `default_transaction_read_only = on` and a statement timeout.
- `scoring.py`: execution match. Column names are ignored, column order is
  ignored, row order is ignored unless the question demands ordering, numerics
  compare with a small tolerance, NULLs compare as NULLs.
- `judge.py`: secondary semantic judge for near-miss analysis, plus the
  calibration sampler that exports a hand-scoring sheet. Judge output is never
  the headline metric.

## Runners

`--runner api` (default) calls the Anthropic Messages API and needs an
`ANTHROPIC_API_KEY`. `--runner claude-cli` reaches the same pinned models
through Claude Code's headless mode (`claude -p`) on a developer subscription
instead. Integrity contract for the CLI runner: each question is answered by a
fresh process launched in an empty temp directory with agentic turns capped at
one, so the subject sees only the schema context and the question, never this
repository or its answer key. The honest caveat, carried in every results
file: the CLI wraps the model in the Claude Code system prompt, so the
measured subject is "model inside Claude Code", not the bare API model, and
any published number names which runner produced it.

## Database access

Local runs execute through a read-only session. For interactive agent access,
the documented deployment is crystaldba/postgres-mcp in `--access-mode
restricted` (parser-based statement gating, read-only transactions, timeouts).
Known limitation to state up front: restricted mode's read-only guarantee can
be bypassed where unsafe procedural-language functions are installed that
manage their own transactions; this database installs none, and the harness
role holds SELECT-only grants as the second layer.

## Why the modeled layer matters

The same questions asked over the raw all-TEXT schema force the model through
date-format parsing, dedup, alias resolution, and the location re-key on every
query; over the marts they do not. Comparing the two conditions (`--schema
raw` flag) is the point of the exercise: modeling discipline is what makes
AI-over-data work, and this harness exists to measure that claim rather than
assert it.
