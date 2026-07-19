# Thin wrapper over cross-platform Python entry points. scripts/setup.ps1 issues
# the identical sequence for PowerShell; keep the two in lockstep.
PY := $(shell test -x .venv/bin/python && echo .venv/bin/python || echo .venv/Scripts/python)

.PHONY: setup venv generate verify calibrate load build psql down nuke ci-check

setup: venv generate verify load

venv:
	python -m venv .venv || py -3.12 -m venv .venv
	$(PY) -m pip install -q -r requirements.txt

generate:
	$(PY) -m generator

verify:
	$(PY) -m generator --verify

calibrate:
	$(PY) -m generator.calibrate

load:
	docker compose up -d --wait
	$(PY) scripts/load.py

DBT := $(shell test -x .venv/bin/dbt && echo .venv/bin/dbt || echo .venv/Scripts/dbt)

# Builds staging views and marts tables and runs every test.
build:
	DBT_PROFILES_DIR=profiles $(DBT) deps
	DBT_PROFILES_DIR=profiles $(DBT) build

psql:
	docker compose exec postgres psql -U mua -d mua

down:
	docker compose down

nuke:
	docker compose down -v

ci-check: verify calibrate
	$(PY) scripts/check_no_wallclock.py
	$(PY) scripts/check_banned_strings.py
