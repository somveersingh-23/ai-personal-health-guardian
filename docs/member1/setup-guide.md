# Member 1 Setup Guide

## Requirements
- Python 3.11+ (Python 3.12 recommended)
- PostgreSQL 16, or Docker Desktop
- Android Studio with JDK 17 and Android SDK 35
- Python packages in `backend/app/requirements.txt`; ML uses pandas and NumPy (install `pandas` and `numpy` if not already installed).

## Python environment — Windows CMD
From the repository root:

```bat
py -3.12 -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r backend\app\requirements.txt pandas numpy
copy .env.example .env
```

Edit `.env` and set a valid `DATABASE_URL`. For a locally installed PostgreSQL server, use `postgresql+asyncpg://health_user:YOUR_PASSWORD@localhost:5432/health_guardian`.

The app's `load_dotenv()` reads `.env` from the current working directory. Start the backend from `backend`:

```bat
cd backend
python -m uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/docs`. The root and `/health` endpoints provide basic service checks.

## Run the Member 1 ML pipeline
From the repository root, with the Python environment active:

```bat
python scripts\run_member1_ml_pipeline.py
```

This creates raw synthetic CSVs and all processed outputs under `ml/member1/data/processed/`. It is safe to rerun; the generator is deterministic for a given seed but timestamps are relative to the run date.

## Docker
From the repository root:

```bat
docker compose config
docker compose up --build -d
docker compose ps
docker compose logs -f backend
```

Before building if you want ML artifact endpoints to return data, run the ML pipeline on the host first. The image copies `ml/` into the image at build time. After changing generated ML artifacts, rebuild the backend image or mount the processed directory explicitly.

Stop containers with `docker compose down`. Add `-v` only if you intentionally want to delete the local PostgreSQL volume and its data.

## Android emulator
The debug app uses `http://10.0.2.2:8000/`, which routes to the host computer from the Android emulator. Keep the backend running. A physical phone must use the computer's LAN IP and both devices must be on the same network. Use HTTPS and restricted origins for any deployed environment.
