param([string]$Container = 'health_guardian_postgres')
$ErrorActionPreference = 'Stop'
$database = 'm2_audit_' + [guid]::NewGuid().ToString('N').Substring(0,12)
$previousDatabaseUrl = $env:DATABASE_URL
$previousTestUrl = $env:M2_POSTGRES_TEST_URL
$created = $false
Push-Location (Join-Path $PSScriptRoot '../backend')
try {
    $info = docker inspect $Container | ConvertFrom-Json
    if ($LASTEXITCODE -ne 0) { throw 'PostgreSQL container not found' }
    $configuration = @{}
    foreach ($entry in $info[0].Config.Env) {
        $parts = $entry.Split('=', 2)
        $configuration[$parts[0]] = $parts[1]
    }
    $dbUser = $configuration['POSTGRES_USER']
    $dbPassword = $configuration['POSTGRES_PASSWORD']
    if (-not $dbUser -or -not $dbPassword) { throw 'Container credentials unavailable' }
    $mapping = $info[0].NetworkSettings.Ports.'5432/tcp' | Select-Object -First 1
    if (-not $mapping) { throw 'PostgreSQL port is not published locally' }
    docker exec $Container createdb -U $dbUser $database
    if ($LASTEXITCODE -ne 0) { throw 'Could not create isolated audit database' }
    $created = $true
    $env:DATABASE_URL = 'postgresql+asyncpg://' + [uri]::EscapeDataString($dbUser) + ':' + [uri]::EscapeDataString($dbPassword) + '@127.0.0.1:' + $mapping.HostPort + '/' + $database
    $env:M2_POSTGRES_TEST_URL = $env:DATABASE_URL
    py -3.14 -m alembic upgrade head
    if ($LASTEXITCODE -ne 0) { throw 'Migration upgrade failed' }
    py -3.14 -m pytest tests/member2/test_postgres_runtime.py tests/member2/test_postgres_concurrency.py -q
    if ($LASTEXITCODE -ne 0) { throw 'PostgreSQL verification failed' }
} finally {
    if ($created) {
        if ($database -notmatch '^m2_audit_[a-f0-9]{12}$') { throw 'Unsafe audit database cleanup target' }
        docker exec $Container dropdb -U $dbUser $database
        if ($LASTEXITCODE -ne 0) { Write-Warning "Temporary audit database needs cleanup: $database" }
    }
    $env:DATABASE_URL = $previousDatabaseUrl
    $env:M2_POSTGRES_TEST_URL = $previousTestUrl
    Pop-Location
}
