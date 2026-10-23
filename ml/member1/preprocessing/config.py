from pathlib import Path

MEMBER1_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = MEMBER1_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"

RAW_NORMAL_DATASET = RAW_DATA_DIR / "synthetic_health_events.csv"
RAW_ANOMALY_DATASET = RAW_DATA_DIR / "synthetic_health_events_with_anomalies.csv"
PROCESSED_NORMAL_DATASET = PROCESSED_DATA_DIR / "normal" / "processed_health_events.csv"
PROCESSED_ANOMALY_DATASET = PROCESSED_DATA_DIR / "anomalies" / "processed_health_events.csv"

SUPPORTED_EVENT_TYPES = {
    "heart_rate",
    "blood_pressure_systolic",
    "blood_pressure_diastolic",
    "blood_glucose",
    "spo2",
    "sleep_duration",
    "steps",
    "calories",
    "water_intake",
    "weight",
}
