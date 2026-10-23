from .baseline_engine import PersonalBaselineEngine
from .config import BASELINE_OUTPUT_FILE, NORMAL_DATASET_FILE


def main() -> None:
    engine = PersonalBaselineEngine()
    baseline = engine.run(NORMAL_DATASET_FILE, BASELINE_OUTPUT_FILE)
    print(f"Saved {len(baseline)} personal baselines to {BASELINE_OUTPUT_FILE}")


if __name__ == "__main__":
    main()
