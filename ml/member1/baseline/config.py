from pathlib import Path

MEMBER1_DIR = Path(__file__).resolve().parents[1]
PROCESSED_DATA_DIR = MEMBER1_DIR / "data" / "processed"
BASELINE_OUTPUT_DIR = PROCESSED_DATA_DIR / "baselines"
BASELINE_OUTPUT_FILE = BASELINE_OUTPUT_DIR / "personal_baselines.csv"
NORMAL_DATASET_FILE = PROCESSED_DATA_DIR / "normal" / "processed_health_events.csv"
MINIMUM_OBSERVATIONS = 10
PERCENTILE_LOW = 0.05
PERCENTILE_HIGH = 0.95
