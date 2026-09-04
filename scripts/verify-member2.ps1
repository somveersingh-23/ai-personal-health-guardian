$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$mlPython = Join-Path $repoRoot "ml/.venv/Scripts/python.exe"
if (-not (Test-Path -LiteralPath $mlPython)) { $mlPython = "python" }

function Assert-ExternalCommandSucceeded {
    param([Parameter(Mandatory = $true)][string]$Step)

    if ($LASTEXITCODE -ne 0) {
        throw "$Step failed with exit code $LASTEXITCODE."
    }
}

function Assert-SystemGradleVersion {
    $versionOutput = gradle --version | Out-String
    if ($LASTEXITCODE -ne 0 -or $versionOutput -notmatch "(?m)^Gradle 9\.5(?:\.0)?\r?$") {
        throw "System Gradle fallback must be version 9.5.x."
    }
}

Push-Location (Join-Path $repoRoot "ml")
try {
    $env:PYTHONPATH = ".;../backend"
    & $mlPython -m ruff check sensor_intelligence tests
    Assert-ExternalCommandSucceeded "ML lint"
    & $mlPython -m compileall -q sensor_intelligence tests
    Assert-ExternalCommandSucceeded "ML compile check"
    & $mlPython -m pytest --cov=sensor_intelligence --cov-report=term --cov-fail-under=55
    Assert-ExternalCommandSucceeded "ML tests"
} finally {
    Pop-Location
}

Push-Location (Join-Path $repoRoot "backend")
try {
    $env:PYTHONPATH = "."
    & $mlPython -m ruff check app tests migrations
    Assert-ExternalCommandSucceeded "Backend lint"
    & $mlPython -m compileall -q app tests migrations
    Assert-ExternalCommandSucceeded "Backend compile check"
    & $mlPython -m pytest tests/member2 -q --cov=app --cov-report=term --cov-fail-under=80
    Assert-ExternalCommandSucceeded "Backend tests"
} finally {
    Pop-Location
}

& $mlPython (Join-Path $repoRoot "scripts/validate-member2-device-evidence.py") `
    (Join-Path $repoRoot "docs/testing/member2-device-evidence.example.json")
Assert-ExternalCommandSucceeded "Device-evidence schema validation"

& $mlPython (Join-Path $repoRoot "scripts/validate-doc-links.py") $repoRoot
Assert-ExternalCommandSucceeded "Documentation link validation"

$userJavaHome = [Environment]::GetEnvironmentVariable("JAVA_HOME", "User")
$userAndroidHome = [Environment]::GetEnvironmentVariable("ANDROID_HOME", "User")
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if (-not $env:JAVA_HOME -and $userJavaHome) { $env:JAVA_HOME = $userJavaHome }
if (-not $env:ANDROID_HOME -and $userAndroidHome) { $env:ANDROID_HOME = $userAndroidHome }
if (-not $env:ANDROID_SDK_ROOT -and $userAndroidHome) { $env:ANDROID_SDK_ROOT = $userAndroidHome }
if ($userPath) { $env:Path = "$userPath;$env:Path" }

$gradleWrapper = Join-Path $repoRoot "mobile/android/gradlew.bat"
$gradle = Get-Command gradle -ErrorAction SilentlyContinue
if ((Test-Path -LiteralPath $gradleWrapper) -and $env:JAVA_HOME -and $env:ANDROID_HOME) {
    Push-Location (Join-Path $repoRoot "mobile/android")
    try {
        & $gradleWrapper --no-daemon testDebugUnitTest lintDebug
        if ($LASTEXITCODE -ne 0 -and $gradle) {
            Write-Warning "Gradle Wrapper could not run; retrying with the installed Gradle runtime."
            Assert-SystemGradleVersion
            gradle --no-daemon testDebugUnitTest lintDebug
            Assert-ExternalCommandSucceeded "Android tests and lint with system Gradle"
        } else {
            Assert-ExternalCommandSucceeded "Android tests and lint"
        }
    } finally {
        Pop-Location
    }
    Write-Host "Member 2 ML, backend and Android verification passed."
} elseif ($gradle -and $env:JAVA_HOME -and $env:ANDROID_HOME) {
    Push-Location (Join-Path $repoRoot "mobile/android")
    try {
        Assert-SystemGradleVersion
        gradle --no-daemon testDebugUnitTest lintDebug
        Assert-ExternalCommandSucceeded "Android tests and lint"
    } finally {
        Pop-Location
    }
    Write-Host "Member 2 ML, backend and Android verification passed with system Gradle."
} else {
    Write-Warning "ML and backend verification passed; Android verification requires JDK 17 and Android SDK 37."
}
