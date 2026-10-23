from pathlib import Path

MEMBER1_DIR = Path(__file__).resolve().parents[1]
PROCESSED_DIR = MEMBER1_DIR / "data" / "processed"
EVENTS_FILE = PROCESSED_DIR / "anomalies" / "processed_health_events.csv"
BASELINE_FILE = PROCESSED_DIR / "baselines" / "personal_baselines.csv"
ANOMALY_FILE = PROCESSED_DIR / "anomalies" / "detected_anomalies.csv"
DIGITAL_TWIN_OUTPUT_DIR = PROCESSED_DIR / "digital_twin"
DIGITAL_TWIN_SNAPSHOT_FILE = DIGITAL_TWIN_OUTPUT_DIR / "digital_twin_snapshot.json"
DIGITAL_TWIN_STATE_FILE = DIGITAL_TWIN_OUTPUT_DIR / "digital_twin_states.csv"
