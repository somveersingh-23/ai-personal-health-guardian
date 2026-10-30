import json
from pathlib import Path

import pandas as pd

from .config import (
    ANOMALY_FILE,
    DIGITAL_TWIN_DIR,
    INSIGHT_CSV_FILE,
    INSIGHT_JSON_FILE,
    INSIGHT_OUTPUT_DIR,
)

from .insight_engine import (
    PersonalizedInsightEngine,
)


def main():

    digital_twin_files = sorted(
        DIGITAL_TWIN_DIR.glob(
            "user_*_state.json"
        )
    )

    if not digital_twin_files:

        raise FileNotFoundError(
            "No per-user Digital Twin "
            "state files were found."
        )

    if ANOMALY_FILE.exists():

        anomalies = pd.read_csv(
            ANOMALY_FILE
        )

    else:

        anomalies = pd.DataFrame()

    engine = (
        PersonalizedInsightEngine()
    )

    all_insights = []

    INSIGHT_OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    for digital_twin_file in (
        digital_twin_files
    ):

        with digital_twin_file.open(
            "r",
            encoding="utf-8",
        ) as file:

            digital_twin = json.load(
                file
            )

        user_id = int(
            digital_twin[
                "user_id"
            ]
        )

        user_anomalies = anomalies

        if (
            not anomalies.empty
            and "user_id" in anomalies.columns
        ):

            user_anomalies = (
                anomalies[
                    anomalies["user_id"]
                    == user_id
                ]
            )

        insights = (
            engine.generate_insights(
                digital_twin=digital_twin,
                anomalies=user_anomalies,
            )
        )

        response = (
            engine.build_response(
                user_id=user_id,
                digital_twin=digital_twin,
                insights=insights,
            )
        )

        user_json_file = (
            INSIGHT_OUTPUT_DIR
            / f"user_{user_id}_insights.json"
        )

        engine.save_json(
            response=response,
            output_file=user_json_file,
        )

        all_insights.extend(
            [
                {
                    "user_id": user_id,
                    **insight,
                }
                for insight in insights
            ]
        )

    # Global JSON file.
    global_response = {
        "generated_at": (
            pd.Timestamp.utcnow()
            .isoformat()
        ),
        "user_count": len(
            digital_twin_files
        ),
        "insight_count": len(
            all_insights
        ),
        "insights": all_insights,
    }

    engine.save_json(
        response=global_response,
        output_file=INSIGHT_JSON_FILE,
    )

    engine.save_csv(
        insights=all_insights,
        output_file=INSIGHT_CSV_FILE,
    )

    print(
        f"Generated insights for "
        f"{len(digital_twin_files)} user(s)."
    )


if __name__ == "__main__":
    main()