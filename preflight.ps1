# Local operator use on X-admin after independently validating package checksum.
# Does not create identity, grant privileges, or alter Canonical/Archive.
$ErrorActionPreference = 'Stop'
if (!(Test-Path -LiteralPath '.\runtime.py')) { throw 'Run from OLGM project root' }
if (!$env:OLGM_DB) { throw 'Set OLGM_DB to the existing dedicated SQLite path first' }
if (!$env:OLGM_HTTP_TOKEN) { throw 'Set OLGM_HTTP_TOKEN securely; never put it in scripts or screenshots' }
$env:OLGM_ENV = 'production'
python runtime.py production-preflight --output 's10_production_preflight.json'
$exit = $LASTEXITCODE
Write-Host "Preflight exit code: $exit (non-zero means NOT APPROVED; inspect JSON)"
exit $exit
