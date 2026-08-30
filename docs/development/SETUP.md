# Development Setup

These instructions are Windows-first because the current verification scripts are PowerShell-based. Equivalent Python, Gradle, and Docker commands work on Linux/macOS.

## Prerequisites

- Git
- Python 3.12 (the validated research/runtime version)
- PowerShell 7 or Windows PowerShell 5.1
- JDK 17
- Android Studio or Android SDK with platform 37
- Docker Desktop with a running Linux-container engine for runtime verification

## 1. Checkout

```powershell
git clone https://github.com/somveersingh-23/ai-personal-health-guardian.git
cd ai-personal-health-guardian
git fetch origin --prune
git switch feature/m2-sensor-intelligence
```

Confirm `git branch --show-current` before editing, committing, or pushing.

## 2. Python environment

Member 2 uses one isolated environment at `ml/.venv`. The ML requirement file includes the backend development requirements so the repository verification script can run both suites with one interpreter.

```powershell
py -3.12 -m venv ml\.venv
ml\.venv\Scripts\python.exe -m pip install --upgrade pip
ml\.venv\Scripts\python.exe -m pip install -r ml\requirements.txt
```

Run the Python checks directly if Android is not being tested:

```powershell
$env:PYTHONPATH = "ml;backend"
ml\.venv\Scripts\python.exe -m pytest ml\tests
ml\.venv\Scripts\python.exe -m pytest backend\tests\member2
```

## 3. Android toolchain

Set `JAVA_HOME` to JDK 17 and `ANDROID_HOME` (or `ANDROID_SDK_ROOT`) to the Android SDK. Install platform 37, accept the SDK licenses, then use the checksum-pinned Gradle wrapper:

```powershell
cd mobile\android
.\gradlew.bat --no-daemon testDebugUnitTest lintDebug
cd ..\..
```

Android hardware/OEM behavior still requires the evidence matrix in `docs/testing/MEMBER2_DEVICE_MATRIX.md`; a desktop JVM build cannot prove device behavior.

## 4. Backend without containers

The canonical runtime dependencies are in `backend/requirements.txt`; development/test tools are in `backend/requirements-dev.txt`. `backend/app/requirements.txt` is only a compatibility shim for the inherited project layout.

```powershell
$env:PYTHONPATH = "backend"
ml\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --reload
```

Development defaults may create a local schema. Production uses PostgreSQL and Alembic and disables preview endpoints.

## 5. Production-mode Docker runtime

Create a local environment file and replace every placeholder. Never commit it.

```powershell
Copy-Item .env.example .env
# Edit .env: use independent, long random values for POSTGRES_PASSWORD and JWT_SECRET.
docker compose config --quiet
docker compose up --build --wait
Invoke-RestMethod http://127.0.0.1:8000/healthz
docker compose down
```

The isolated smoke test uses the safe example configuration, a random local port, a separate Compose project, verifies migrations/tables/API health, and removes its temporary volume:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\verify-docker-runtime.ps1
```

## 6. Full Member 2 gate

```powershell
powershell -ExecutionPolicy Bypass -File scripts\verify-member2.ps1
```

## Research datasets

Raw datasets are not needed for normal unit tests and must not be committed. Read `docs/research/MEMBER2_DATASETS.md` and each source's terms before opt-in acquisition:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\download-member2-data.ps1 bidmc
```

The downloader validates registered sources and stores data only under the ignored local `data/` tree. Results are research evidence, not clinical validation.

## Troubleshooting

- If `py -3.12` is missing, install Python 3.12 and recreate `ml/.venv`; do not run research dependencies under an arbitrary interpreter.
- If Gradle cannot locate Android, verify `JAVA_HOME`, `ANDROID_HOME`, SDK platform 37, and accepted licenses.
- If Docker reports that the engine is unavailable, start Docker Desktop and wait for `docker info` to succeed.
- If a port is occupied, set a different `BACKEND_PORT` in the local `.env`.
- Before reporting a failure, capture the exact command, first error, current branch, and tool versions—never secrets or health records.
