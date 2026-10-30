from __future__ import annotations

from pathlib import Path

import pandas as pd

from .config import (
    BASELINE_OUTPUT_FILE,
    BASELINE_OUTPUT_DIR,
    MINIMUM_OBSERVATIONS,
    PERCENTILE_HIGH,
    PERCENTILE_LOW,
)


class PersonalBaselineEngine:
    """
    Calculates personalized statistical baselines
    for individual users and health metrics.
    """

    def __init__(
        self,
        minimum_observations: int = MINIMUM_OBSERVATIONS,
    ):
        self.minimum_observations = (
            minimum_observations
        )

    @staticmethod
    def validate_dataset(
        df: pd.DataFrame,
    ) -> None:

        required_columns = [
            "user_id",
            "event_type",
            "event_time",
            "value",
        ]

        missing = [
            column
            for column in required_columns
            if column not in df.columns
        ]

        if missing:
            raise ValueError(
                "Missing required columns: "
                + ", ".join(missing)
            )

    def calculate_baselines(
        self,
        df: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Calculate personalized statistical baselines.
        """

        self.validate_dataset(df)

        data = df.copy()

        data["value"] = pd.to_numeric(
            data["value"],
            errors="coerce",
        )

        data["event_time"] = pd.to_datetime(
            data["event_time"],
            errors="coerce",
            utc=True,
        )

        data = data.dropna(
            subset=[
                "user_id",
                "event_type",
                "event_time",
                "value",
            ]
        )

        grouped = data.groupby(
            [
                "user_id",
                "event_type",
            ]
        )

        baseline = grouped["value"].agg(
            observation_count="count",
            mean="mean",
            median="median",
            std="std",
            minimum="min",
            maximum="max",
        ).reset_index()

        percentile_low = (
            grouped["value"]
            .quantile(PERCENTILE_LOW)
            .reset_index(
                name="percentile_05"
            )
        )

        percentile_high = (
            grouped["value"]
            .quantile(PERCENTILE_HIGH)
            .reset_index(
                name="percentile_95"
            )
        )

        baseline = baseline.merge(
            percentile_low,
            on=[
                "user_id",
                "event_type",
            ],
            how="left",
        )

        baseline = baseline.merge(
            percentile_high,
            on=[
                "user_id",
                "event_type",
            ],
            how="left",
        )

        # Standard deviation is undefined for one observation.
        baseline["std"] = (
            baseline["std"]
            .fillna(0)
        )

        # Personal baseline boundaries.
        baseline["lower_bound"] = (
            baseline["percentile_05"]
        )

        baseline["upper_bound"] = (
            baseline["percentile_95"]
        )

        baseline["mean_plus_2std"] = (
            baseline["mean"]
            + (
                2
                * baseline["std"]
            )
        )

        baseline["mean_minus_2std"] = (
            baseline["mean"]
            - (
                2
                * baseline["std"]
            )
        )

        baseline["mean_plus_3std"] = (
            baseline["mean"]
            + (
                3
                * baseline["std"]
            )
        )

        baseline["mean_minus_3std"] = (
            baseline["mean"]
            - (
                3
                * baseline["std"]
            )
        )

        # Ensure lower statistical boundaries
        # cannot become negative for metrics
        # that cannot logically be negative.
        baseline["mean_minus_2std"] = (
            baseline["mean_minus_2std"]
            .clip(lower=0)
        )

        baseline["mean_minus_3std"] = (
            baseline["mean_minus_3std"]
            .clip(lower=0)
        )

        # Baseline quality.
        baseline["baseline_quality"] = (
            baseline["observation_count"]
            .apply(
                self._calculate_quality
            )
        )

        return baseline

    def _calculate_quality(
        self,
        observation_count: int,
    ) -> str:

        if observation_count < 3:
            return "insufficient"

        if observation_count < 10:
            return "low"

        if observation_count < 30:
            return "moderate"

        return "strong"

    def calculate_daily_baselines(
        self,
        df: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Calculate daily personal statistics.
        """

        self.validate_dataset(df)

        data = df.copy()

        data["event_time"] = pd.to_datetime(
            data["event_time"],
            errors="coerce",
            utc=True,
        )

        data["value"] = pd.to_numeric(
            data["value"],
            errors="coerce",
        )

        data = data.dropna(
            subset=[
                "user_id",
                "event_type",
                "event_time",
                "value",
            ]
        )

        data["date"] = (
            data["event_time"]
            .dt.date
        )

        daily = (
            data.groupby(
                [
                    "user_id",
                    "event_type",
                    "date",
                ]
            )["value"]
            .agg(
                daily_mean="mean",
                daily_median="median",
                daily_min="min",
                daily_max="max",
                daily_std="std",
                observation_count="count",
            )
            .reset_index()
        )

        daily["daily_std"] = (
            daily["daily_std"]
            .fillna(0)
        )

        return daily

    def save_baselines(
        self,
        baseline_df: pd.DataFrame,
        output_file: Path = BASELINE_OUTPUT_FILE,
    ) -> None:

        output_file.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        baseline_df.to_csv(
            output_file,
            index=False,
        )

    def run(
        self,
        input_file: Path,
        output_file: Path = BASELINE_OUTPUT_FILE,
    ) -> pd.DataFrame:

        if not input_file.exists():
            raise FileNotFoundError(
                f"Input dataset not found: {input_file}"
            )

        df = pd.read_csv(
            input_file
        )

        baseline = (
            self.calculate_baselines(df)
        )

        # Only baselines with sufficient observations
        # should be treated as usable.
        usable = baseline[
            baseline["observation_count"]
            >= self.minimum_observations
        ].copy()

        self.save_baselines(
            usable,
            output_file,
        )

        return usable