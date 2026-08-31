param(
    [switch]$KeepContainers
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$composeFile = Join-Path $repoRoot "docker-compose.yml"
$exampleEnvironment = Join-Path $repoRoot ".env.example"
$smokeProject = "health-guardian-member2-smoke"
$cleanupRequired = $false
$previousBackendPort = [Environment]::GetEnvironmentVariable("BACKEND_PORT", "Process")
$previousProcessPath = [Environment]::GetEnvironmentVariable("Path", "Process")

function Resolve-DockerExecutable {
    $command = Get-Command docker -ErrorAction SilentlyContinue
    if ($command) {
        return $command.Source
    }

    $candidates = @(
        (Join-Path $env:LOCALAPPDATA "Programs/DockerDesktop/resources/bin/docker.exe"),
        (Join-Path $env:ProgramFiles "Docker/Docker/resources/bin/docker.exe")
    )
    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate) {
            return $candidate
        }
    }

    throw "Docker CLI was not found. Install Docker Desktop and restart Windows before running this check."
}

function Assert-ExternalCommandSucceeded {
    param([Parameter(Mandatory = $true)][string]$Step)

    if ($LASTEXITCODE -ne 0) {
        throw "$Step failed with exit code $LASTEXITCODE."
    }
}

if (-not (Test-Path -LiteralPath $composeFile)) {
    throw "Compose file not found: $composeFile"
}
if (-not (Test-Path -LiteralPath $exampleEnvironment)) {
    throw "Example environment file not found: $exampleEnvironment"
}

$dockerExecutable = Resolve-DockerExecutable
$dockerBinaryDirectory = Split-Path -Parent $dockerExecutable
$env:Path = "$dockerBinaryDirectory;$previousProcessPath"
$composeArguments = @(
    "compose",
    "--project-name", $smokeProject,
    "--env-file", $exampleEnvironment,
    "--file", $composeFile
)

$portProbe = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, 0)
$portProbe.Start()
$smokePort = ([System.Net.IPEndPoint]$portProbe.LocalEndpoint).Port
$portProbe.Stop()
$env:BACKEND_PORT = $smokePort.ToString()

Push-Location $repoRoot
try {
    & $dockerExecutable @composeArguments config --quiet
    Assert-ExternalCommandSucceeded "Docker Compose configuration validation"

    & $dockerExecutable info --format "Docker server {{.ServerVersion}}"
    if ($LASTEXITCODE -ne 0) {
        throw (
            "Docker Desktop is installed, but its engine is not available. " +
            "Open Docker Desktop, resolve any displayed startup error, wait until the engine is running, " +
            "and retry this script."
        )
    }

    $cleanupRequired = $true
    & $dockerExecutable @composeArguments up --build --detach --wait --wait-timeout 240
    Assert-ExternalCommandSucceeded "Docker Compose build and startup"

    $health = Invoke-RestMethod -Uri "http://127.0.0.1:$smokePort/healthz" -Method Get -TimeoutSec 15
    if ($health.status -ne "ok") {
        throw "Backend health endpoint returned an unexpected response."
    }

    $revisionOutput = & $dockerExecutable @composeArguments exec --no-TTY postgres psql `
        --username health_user --dbname health_guardian --tuples-only --no-align `
        --set ON_ERROR_STOP=1 --command "SELECT version_num FROM alembic_version;"
    Assert-ExternalCommandSucceeded "Alembic revision inspection"
    $migrationRevision = ($revisionOutput | Out-String).Trim()
    if ($migrationRevision -ne "0002_member2") {
        throw "Unexpected Alembic revision: $migrationRevision"
    }

    $tableQuery = "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_name IN ('health_profiles', 'health_events', 'sensor_ingestion_audits', 'device_registries', 'health_connect_sync_states', 'consent_receipts', 'device_capabilities', 'source_tombstones', 'reconciliation_sessions', 'reconciliation_records');"
    $tableOutput = & $dockerExecutable @composeArguments exec --no-TTY postgres psql `
        --username health_user --dbname health_guardian --tuples-only --no-align `
        --set ON_ERROR_STOP=1 --command $tableQuery
    Assert-ExternalCommandSucceeded "Migrated table inspection"
    $migratedTableCount = ($tableOutput | Out-String).Trim()
    if ($migratedTableCount -ne "10") {
        throw "Expected ten application tables after migration; found $migratedTableCount."
    }

    $columnQuery = "SELECT COUNT(*) FROM information_schema.columns WHERE table_schema = 'public' AND (table_name, column_name) IN (('health_events', 'canonical_unit_ucum'), ('health_events', 'quality_vector_json'), ('health_events', 'consent_receipt_id'), ('health_connect_sync_states', 'token_fingerprint'));"
    $columnOutput = & $dockerExecutable @composeArguments exec --no-TTY postgres psql `
        --username health_user --dbname health_guardian --tuples-only --no-align `
        --set ON_ERROR_STOP=1 --command $columnQuery
    Assert-ExternalCommandSucceeded "Governed-observation column inspection"
    $governedColumnCount = ($columnOutput | Out-String).Trim()
    if ($governedColumnCount -ne "4") {
        throw "Expected four governed-observation columns; found $governedColumnCount."
    }

    $token = & $dockerExecutable @composeArguments exec --no-TTY backend python -c `
        "from app.core.config import settings; from app.core.security import create_access_token; print(create_access_token(4242, settings, 5))"
    Assert-ExternalCommandSucceeded "Runtime smoke-token creation"
    $token = ($token | Out-String).Trim()
    if (-not $token) {
        throw "Runtime smoke-token creation returned no token."
    }
    $headers = @{ Authorization = "Bearer $token" }
    $baseUri = "http://127.0.0.1:$smokePort/api/v1/member2"
    $claims = Invoke-RestMethod -Uri "$baseUri/claims" -Headers $headers -Method Get -TimeoutSec 15
    $cameraSpO2 = $claims | Where-Object { $_.feature_id -eq "phone-camera-spo2" }
    if (-not $cameraSpO2 -or $cameraSpO2.claim_class -ne "prohibited") {
        throw "Runtime claim registry did not prohibit phone-camera SpO2."
    }

    $now = [DateTimeOffset]::UtcNow
    $receiptId = [Guid]::NewGuid().ToString()
    $consentBody = @{
        receipt_id = $receiptId
        purpose = "sensor_intelligence_wellness"
        purpose_version = "wellness-v1"
        notice_version = "smoke-privacy-v1"
        granted_metrics = @("steps")
        granted_sources = @("health_connect")
        consented_at = $now.AddMinutes(-1).ToString("o")
        expires_at = $now.AddDays(1).ToString("o")
    } | ConvertTo-Json -Depth 5
    $consent = Invoke-RestMethod -Uri "$baseUri/consents" -Headers $headers -Method Post `
        -ContentType "application/json" -Body $consentBody -TimeoutSec 15
    if ($consent.receipt_id -ne $receiptId -or $consent.status -ne "active") {
        throw "PostgreSQL consent persistence returned an unexpected response."
    }

    $recordId = "docker-smoke-$([Guid]::NewGuid().ToString('N'))"
    $eventBody = @{
        schema_version = "3.0.0"
        events = @(@{
            schema_version = "3.0.0"
            source = "health_connect"
            temporal_type = "interval"
            metric = "steps"
            unit = "count"
            start_at = $now.AddMinutes(-10).ToString("o")
            end_at = $now.AddMinutes(-5).ToString("o")
            value = 120
            data_origin_package = "org.healthguardian.docker.smoke"
            source_record_type = "StepsRecord"
            source_record_id = $recordId
            source_last_modified_at = $now.AddMinutes(-2).ToString("o")
            recording_method = "automatically_recorded"
            permission_state = "granted_background"
            consent_receipt_id = $receiptId
            processing_purpose = "sensor_intelligence_wellness"
            purpose_version = "wellness-v1"
            retention_class = "normalized_observation"
            mapper_version = "docker-smoke-v3"
            wear_state = "worn"
            motion_state = "moving"
        })
    } | ConvertTo-Json -Depth 8
    $ingestion = Invoke-RestMethod -Uri "$baseUri/events/batch" -Headers $headers -Method Post `
        -ContentType "application/json" -Body $eventBody -TimeoutSec 15
    $event = $ingestion.events | Select-Object -First 1
    if (
        $ingestion.inserted_count -ne 1 -or
        $event.canonical_unit_ucum -ne "{count}" -or
        $event.standard_code -ne "41950-7"
    ) {
        throw "Governed v3 PostgreSQL ingestion did not preserve canonical unit/code output."
    }

    $withdrawalBody = @{
        delete_linked_observations = $true
        reason = "docker_smoke_cleanup"
    } | ConvertTo-Json
    $withdrawal = Invoke-RestMethod -Uri "$baseUri/consents/$receiptId/withdraw" `
        -Headers $headers -Method Post -ContentType "application/json" `
        -Body $withdrawalBody -TimeoutSec 15
    if ($withdrawal.status -ne "withdrawn" -or $withdrawal.deleted_observation_count -ne 1) {
        throw "Consent withdrawal did not delete the governed smoke observation."
    }

    & $dockerExecutable @composeArguments ps
    Assert-ExternalCommandSucceeded "Docker Compose service inspection"
    Write-Host "Docker runtime smoke test passed: revision 0002_member2, ten tables, v3 claims/consent/ingestion/withdrawal and backend health checks succeeded."
} finally {
    if ($cleanupRequired -and -not $KeepContainers) {
        & $dockerExecutable @composeArguments down --volumes --remove-orphans
        if ($LASTEXITCODE -ne 0) {
            Write-Warning "Smoke-test cleanup did not complete; project name: $smokeProject"
        }
    }
    [Environment]::SetEnvironmentVariable("BACKEND_PORT", $previousBackendPort, "Process")
    [Environment]::SetEnvironmentVariable("Path", $previousProcessPath, "Process")
    Pop-Location
}
