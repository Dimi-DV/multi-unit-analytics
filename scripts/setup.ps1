# One-command setup for PowerShell. Mirrors the Makefile targets exactly;
# keep the two in lockstep.
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

if (-not (Test-Path ".venv")) {
    try { python -m venv .venv } catch { py -3.12 -m venv .venv }
}
& .venv\Scripts\python.exe -m pip install -q -r requirements.txt

& .venv\Scripts\python.exe -m generator
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& .venv\Scripts\python.exe -m generator --verify
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

docker compose up -d --wait
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& .venv\Scripts\python.exe scripts\load.py
exit $LASTEXITCODE
