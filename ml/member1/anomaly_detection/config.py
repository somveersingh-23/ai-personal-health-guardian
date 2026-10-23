from pathlib import Path

MEMBER1_DIR = Path(__file__).resolve().parents[1]
PROCESSED_DIR = MEMBER1_DIR / "data" / "processed"
INPUT_DATASET = PROCESSED_DIR / "anomalies" / "processed_health_events.csv"
BASELINE_FILE = PROCESSED_DIR / "baselines" / "personal_baselines.csv"
ANOMALY_OUTPUT_DIR = PROCESSED_DIR / "anomalies"
ANOMALY_OUTPUT_FILE = ANOMALY_OUTPUT_DIR / "detected_anomalies.csv"

# Statistical thresholds are development defaults, not clinical thresholds.
MIN_ABSOLUTE_Z_SCORE = 2.5
HIGH_Z_SCORE = 3.5
