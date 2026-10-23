"""Run the complete Member 1 synthetic-data → insight artifact pipeline.

Run from the repository root:
    python scripts/run_member1_ml_pipeline.py
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ml.member1.data.generate_synthetic_health_data import generate
from ml.member1.preprocessing.preprocessing import preprocess_all
from ml.member1.baseline.baseline_engine import PersonalBaselineEngine
from ml.member1.baseline.config import BASELINE_OUTPUT_FILE, NORMAL_DATASET_FILE
from ml.member1.anomaly_detection.anomaly_engine import AnomalyDetectionEngine
from ml.member1.digital_twin.run_digital_twin import main as build_digital_twins
from ml.member1.inshights.run_insights import main as build_insights


def main() -> None:
    print("[1/6] Generating synthetic health events...")
    generate()

    print("[2/6] Preprocessing normal and anomaly datasets...")
    preprocess_all()

    print("[3/6] Calculating personal baselines from normal data...")
    baselines = PersonalBaselineEngine().run(NORMAL_DATASET_FILE, BASELINE_OUTPUT_FILE)
    if baselines.empty:
        raise RuntimeError("No usable baselines were produced. Check the input dataset.")

    print("[4/6] Scoring events against personal baselines...")
    scored = AnomalyDetectionEngine().run()
    if scored.empty:
        raise RuntimeError("Anomaly engine produced no scored events.")

    print("[5/6] Building per-user Digital Twin states...")
    build_digital_twins()

    print("[6/6] Generating personalized insights...")
    build_insights()

    print("Member 1 ML pipeline completed.")
    print("Generated files are under ml/member1/data/processed/.")


if __name__ == "__main__":
    main()
