from __future__ import annotations

from pathlib import Path

import pandas as pd

from .config import (
    PROCESSED_DATA_DIR,
    PROCESSED_ANOMALY_DATASET,
    PROCESSED_NORMAL_DATASET,
    SUPPORTED_EVENT_TYPES,
)


REQUIRED_COLUMNS = [
    "event_id",
    "user_id",
    "event_type",
    "event_time",
    "value",
    "unit",
    "source",
    "notes",
]


def load_dataset(file_path: Path) -> pd.DataFrame:
    """
    Load a raw health-event CSV dataset.
    """

    if not file_path.exists():
        raise FileNotFoundError(
            f"Dataset not found: {file_path}"
        )

    df = pd.read_csv(file_path)

    return df


def validate_columns(df: pd.DataFrame) -> None:
    """
    Ensure all required columns exist.
    """

    missing_columns = [
        column
        for column in REQUIRED_COLUMNS
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            "Missing required columns: "
            + ", ".join(missing_columns)
        )


def clean_dataset(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean and standardize raw health-event data.
    """

    validate_columns(df)

    cleaned = df.copy()

    # Normalize column names.
    cleaned.columns = (
        cleaned.columns
        .str.strip()
        .str.lower()
    )

    # Convert event ID and user ID.
    cleaned["event_id"] = pd.to_numeric(
        cleaned["event_id"],
        errors="coerce",
    )

    cleaned["user_id"] = pd.to_numeric(
        cleaned["user_id"],
        errors="coerce",
    )

    # Convert value to numeric.
    cleaned["value"] = pd.to_numeric(
        cleaned["value"],
        errors="coerce",
    )

    # Convert timestamp.
    cleaned["event_time"] = pd.to_datetime(
        cleaned["event_time"],
        errors="coerce",
        utc=True,
    )

    # Normalize strings.
    for column in [
        "event_type",
        "unit",
        "source",
        "notes",
    ]:
        cleaned[column] = (
            cleaned[column]
            .fillna("")
            .astype(str)
            .str.strip()
        )

    # Normalize event type.
    cleaned["event_type"] = (
        cleaned["event_type"]
        .str.lower()
        .str.replace(" ", "_")
    )

    # Remove rows with invalid critical fields.
    cleaned = cleaned.dropna(
        subset=[
            "event_id",
            "user_id",
            "event_time",
            "value",
        ]
    )

    # Keep only supported health measurements.
    cleaned = cleaned[
        cleaned["event_type"].isin(
            SUPPORTED_EVENT_TYPES
        )
    ]

    # Remove duplicate events.
    cleaned = cleaned.drop_duplicates(
        subset=["event_id"],
        keep="first",
    )

    # Remove impossible negative values for measurements
    # where negative values are not meaningful.
    non_negative_metrics = [
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
    ]

    for metric in non_negative_metrics:
        mask = cleaned["event_type"] == metric

        cleaned.loc[
            mask & (cleaned["value"] < 0),
            "value",
        ] = pd.NA

    cleaned = cleaned.dropna(
        subset=["value"]
    )

    # Sort chronologically.
    cleaned = cleaned.sort_values(
        by=[
            "user_id",
            "event_time",
            "event_id",
        ]
    )

    # Reset index.
    cleaned = cleaned.reset_index(
        drop=True
    )

    return cleaned


def add_time_features(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Add useful temporal features for ML.
    """

    result = df.copy()

    result["date"] = (
        result["event_time"]
        .dt.date
    )

    result["hour"] = (
        result["event_time"]
        .dt.hour
    )

    result["day_of_week"] = (
        result["event_time"]
        .dt.dayofweek
    )

    result["day_of_month"] = (
        result["event_time"]
        .dt.day
    )

    result["week_of_year"] = (
        result["event_time"]
        .dt.isocalendar()
        .week
        .astype(int)
    )

    return result


def add_rolling_features(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Calculate rolling statistics independently
    for each user and metric.
    """

    result = df.copy()

    result = result.sort_values(
        [
            "user_id",
            "event_type",
            "event_time",
        ]
    )

    grouped = result.groupby(
        [
            "user_id",
            "event_type",
        ],
        group_keys=False,
    )

    result["rolling_mean_3"] = (
        grouped["value"]
        .transform(
            lambda series:
            series.rolling(
                window=3,
                min_periods=1,
            ).mean()
        )
    )

    result["rolling_std_3"] = (
        grouped["value"]
        .transform(
            lambda series:
            series.rolling(
                window=3,
                min_periods=1,
            ).std()
        )
    )

    result["rolling_mean_7"] = (
        grouped["value"]
        .transform(
            lambda series:
            series.rolling(
                window=7,
                min_periods=1,
            ).mean()
        )
    )

    result["rolling_std_7"] = (
        grouped["value"]
        .transform(
            lambda series:
            series.rolling(
                window=7,
                min_periods=1,
            ).std()
        )
    )

    result["rolling_std_3"] = (
        result["rolling_std_3"]
        .fillna(0)
    )

    result["rolling_std_7"] = (
        result["rolling_std_7"]
        .fillna(0)
    )

    return result


def add_change_features(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Calculate changes between consecutive observations.
    """

    result = df.copy()

    result = result.sort_values(
        [
            "user_id",
            "event_type",
            "event_time",
        ]
    )

    grouped = result.groupby(
        [
            "user_id",
            "event_type",
        ],
        group_keys=False,
    )

    result["previous_value"] = (
        grouped["value"]
        .shift(1)
    )

    result["value_change"] = (
        result["value"]
        - result["previous_value"]
    )

    result["percentage_change"] = (
        (
            result["value_change"]
            / result["previous_value"]
        )
        * 100
    )

    result["percentage_change"] = (
        result["percentage_change"]
        .replace(
            [float("inf"), float("-inf")],
            pd.NA,
        )
    )

    result["percentage_change"] = (
        result["percentage_change"]
        .fillna(0)
    )

    result["value_change"] = (
        result["value_change"]
        .fillna(0)
    )

    return result


def create_feature_dataset(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Build the final feature dataset used
    by the baseline and anomaly engines.
    """

    result = add_time_features(df)

    result = add_rolling_features(result)

    result = add_change_features(result)

    result = result.sort_values(
        [
            "user_id",
            "event_time",
            "event_id",
        ]
    )

    result = result.reset_index(
        drop=True
    )

    return result


def preprocess_file(
    input_file: Path,
    output_file: Path,
) -> pd.DataFrame:
    """
    Complete preprocessing pipeline.
    """

    df = load_dataset(input_file)

    cleaned = clean_dataset(df)

    features = create_feature_dataset(
        cleaned
    )

    PROCESSED_DATA_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    features.to_csv(
        output_file,
        index=False,
    )

    return features


def preprocess_all() -> None:
    """
    Preprocess both normal and anomaly datasets.
    """

    preprocess_file(
        input_file=(
            PROCESSED_DATA_DIR.parent
            / "raw"
            / "synthetic_health_events.csv"
        ),
        output_file=PROCESSED_NORMAL_DATASET,
    )

    preprocess_file(
        input_file=(
            PROCESSED_DATA_DIR.parent
            / "raw"
            / "synthetic_health_events_with_anomalies.csv"
        ),
        output_file=PROCESSED_ANOMALY_DATASET,
    )

    print(
        "Preprocessing completed successfully."
    )


if __name__ == "__main__":
    preprocess_all()