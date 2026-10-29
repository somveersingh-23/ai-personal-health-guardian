from pathlib import Path

import pandas as pd

from .config import (
    ANOMALY_FILE,
    DIGITAL_TWIN_OUTPUT_DIR,
    DIGITAL_TWIN_SNAPSHOT_FILE,
    DIGITAL_TWIN_STATE_FILE,
    EVENTS_FILE,
    BASELINE_FILE,
)

from .state_engine import (
    DigitalTwinStateEngine,
)


def main():

    if not EVENTS_FILE.exists():
        raise FileNotFoundError(
            f"Events file not found: {EVENTS_FILE}"
        )

    if not BASELINE_FILE.exists():
        raise FileNotFoundError(
            f"Baseline file not found: {BASELINE_FILE}"
        )

    if not ANOMALY_FILE.exists():
        raise FileNotFoundError(
            f"Anomaly file not found: {ANOMALY_FILE}"
        )

    events = pd.read_csv(
        EVENTS_FILE
    )

    baselines = pd.read_csv(
        BASELINE_FILE
    )

    anomalies = pd.read_csv(
        ANOMALY_FILE
    )

    if events.empty:
        raise ValueError(
            "Health event dataset is empty."
        )

    user_ids = sorted(
        events["user_id"]
        .dropna()
        .astype(int)
        .unique()
        .tolist()
    )

    engine = (
        DigitalTwinStateEngine()
    )

    DIGITAL_TWIN_OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    all_states = []

    for user_id in user_ids:

        state = engine.build_state(
            events=events,
            baselines=baselines,
            anomalies=anomalies,
            user_id=user_id,
        )

        user_state_file = (
            DIGITAL_TWIN_OUTPUT_DIR
            / f"user_{user_id}_state.json"
        )

        engine.save_state(
            state=state,
            output_file=user_state_file,
        )

        metric_file = (
            DIGITAL_TWIN_OUTPUT_DIR
            / f"user_{user_id}_metrics.csv"
        )

        engine.save_metric_state_table(
            state=state,
            output_file=metric_file,
        )

        all_states.append(state)

    # Save the first/primary user as a snapshot
    # for the current synthetic development setup.
    primary_state = all_states[0]

    engine.save_state(
        state=primary_state,
        output_file=DIGITAL_TWIN_SNAPSHOT_FILE,
    )

    # Create a compact state table.
    summary_rows = []

    for state in all_states:

        summary_rows.append(
            {
                "user_id": state[
                    "user_id"
                ],
                "generated_at": state[
                    "generated_at"
                ],
                "state": state[
                    "state"
                ],
                "anomaly_score": state[
                    "anomaly_score"
                ],
                "total_events": state[
                    "summary"
                ]["total_events"],
                "total_anomalies": state[
                    "summary"
                ]["total_anomalies"],
                "high_anomalies": state[
                    "summary"
                ]["high_anomalies"],
                "moderate_anomalies": state[
                    "summary"
                ]["moderate_anomalies"],
                "low_anomalies": state[
                    "summary"
                ]["low_anomalies"],
            }
        )

    pd.DataFrame(
        summary_rows
    ).to_csv(
        DIGITAL_TWIN_STATE_FILE,
        index=False,
    )

    print(
        f"Generated Digital Twin states "
        f"for {len(all_states)} user(s)."
    )


if __name__ == "__main__":
    main()