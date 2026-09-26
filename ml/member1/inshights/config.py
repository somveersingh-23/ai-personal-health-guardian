from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]

PROCESSED_DATA_DIR = (
    BASE_DIR
    / "data"
    / "processed"
)

DIGITAL_TWIN_DIR = (
    PROCESSED_DATA_DIR
    / "digital_twin"
)

ANOMALY_FILE = (
    PROCESSED_DATA_DIR
    / "anomalies"
    / "detected_anomalies.csv"
)

BASELINE_FILE = (
    PROCESSED_DATA_DIR
    / "baselines"
    / "personal_baselines.csv"
)

INSIGHT_OUTPUT_DIR = (
    PROCESSED_DATA_DIR
    / "insights"
)

INSIGHT_JSON_FILE = (
    INSIGHT_OUTPUT_DIR
    / "personalized_insights.json"
)

INSIGHT_CSV_FILE = (
    INSIGHT_OUTPUT_DIR
    / "personalized_insights.csv"
)