param([int]$Port = 8001)
$ErrorActionPreference = 'Stop'
if ($Port -lt 1 -or $Port -gt 65535) { throw 'Port must be between 1 and 65535' }
Push-Location (Join-Path $PSScriptRoot '../backend')
try {
    # DATABASE_URL is provided by the caller or backend/.env. No credentials in source.
    py -3.14 -m uvicorn app.api.member2.application:create_app --factory --host 127.0.0.1 --port $Port
    if ($LASTEXITCODE -ne 0) { throw 'Member 2 server exited unsuccessfully' }
} finally { Pop-Location }
