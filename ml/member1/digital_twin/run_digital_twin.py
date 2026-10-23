import pandas as pd

from .config import (
    ANOMALY_FILE,
    BASELINE_FILE,
    DIGITAL_TWIN_OUTPUT_DIR,
    DIGITAL_TWIN_SNAPSHOT_FILE,
    DIGITAL_TWIN_STATE_FILE,
    EVENTS_FILE,
)
from .state_engine import DigitalTwinStateEngine


def main() -> None:
    for file_path in (EVENTS_FILE, BASELINE_FILE, ANOMALY_FILE):
        if not file_path.is_file():
            raise FileNotFoundError(f"Required ML artifact not found: {file_path}")

    events = pd.read_csv(EVENTS_FILE)
    baselines = pd.read_csv(BASELINE_FILE)
    anomalies = pd.read_csv(ANOMALY_FILE)
    if events.empty:
        raise ValueError("Health event dataset is empty.")

    user_ids = sorted(pd.to_numeric(events["user_id"], errors="coerce").dropna().astype(int).unique())
    if not user_ids:
        raise ValueError("No valid user IDs found in the event dataset.")

    engine = DigitalTwinStateEngine()
    DIGITAL_TWIN_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    states = []

    for user_id in user_ids:
        state = engine.build_state(events, baselines, anomalies, int(user_id))
        engine.save_state(state, DIGITAL_TWIN_OUTPUT_DIR / f"user_{user_id}_state.json")
        engine.save_metric_state_table(state, DIGITAL_TWIN_OUTPUT_DIR / f"user_{user_id}_metrics.csv")
        states.append(state)

    engine.save_state(states[0], DIGITAL_TWIN_SNAPSHOT_FILE)
    pd.DataFrame([{
        "user_id": state["user_id"],
        "generated_at": state["generated_at"],
        "state": state["state"],
        "anomaly_score": state["anomaly_score"],
        **state["summary"],
    } for state in states]).to_csv(DIGITAL_TWIN_STATE_FILE, index=False)

    print(f"Generated Digital Twin states for {len(states)} user(s).")


if __name__ == "__main__":
    main()
