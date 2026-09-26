from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


class PersonalizedInsightEngine:
    """
    Generates structured personalized health insights
    from the Digital Twin state, anomaly results,
    and personal baselines.

    This engine provides data-driven observations.
    It does not provide a medical diagnosis.
    """

    SEVERITY_PRIORITY = {
        "high": 3,
        "moderate": 2,
        "low": 1,
    }

    def __init__(
        self,
        maximum_insights: int = 10,
    ):
        self.maximum_insights = (
            maximum_insights
        )

    @staticmethod
    def _safe_float(
        value,
        default=0.0,
    ) -> float:

        try:
            if pd.isna(value):
                return default

            return float(value)

        except (
            TypeError,
            ValueError,
        ):
            return default

    @staticmethod
    def _priority_from_severity(
        severity: str,
    ) -> int:

        return {
            "high": 3,
            "moderate": 2,
            "low": 1,
        }.get(
            severity,
            0,
        )

    def _anomaly_insight(
        self,
        anomaly: dict,
    ) -> dict:

        event_type = str(
            anomaly.get(
                "event_type",
                "health metric",
            )
        )

        severity = str(
            anomaly.get(
                "severity",
                "low",
            )
        )

        confidence = self._safe_float(
            anomaly.get(
                "confidence",
                0,
            )
        )

        value = self._safe_float(
            anomaly.get(
                "value",
                0,
            )
        )

        explanation = str(
            anomaly.get(
                "explanation",
                "",
            )
        )

        if severity == "high":

            title = (
                f"Significant change in "
                f"{event_type.replace('_', ' ')}"
            )

            message = (
                f"The latest {event_type.replace('_', ' ')} "
                f"value ({value:g}) shows a substantial "
                f"deviation from the user's personal "
                f"historical pattern."
            )

            action = (
                "Review the recent measurements and "
                "consider whether additional monitoring "
                "or professional medical advice is appropriate."
            )

        elif severity == "moderate":

            title = (
                f"Change detected in "
                f"{event_type.replace('_', ' ')}"
            )

            message = (
                f"The latest {event_type.replace('_', ' ')} "
                f"value differs noticeably from the user's "
                f"personal baseline."
            )

            action = (
                "Continue monitoring this metric and "
                "compare it with subsequent measurements."
            )

        else:

            title = (
                f"Minor change in "
                f"{event_type.replace('_', ' ')}"
            )

            message = (
                f"A smaller-than-usual change was detected "
                f"in {event_type.replace('_', ' ')}."
            )

            action = (
                "Continue following the metric over time."
            )

        return {
            "insight_type": "anomaly",
            "category": "monitoring",
            "severity": severity,
            "priority": self._priority_from_severity(
                severity
            ),
            "confidence": round(
                confidence,
                3,
            ),
            "title": title,
            "message": message,
            "recommended_action": action,
            "supporting_data": {
                "event_type": event_type,
                "value": value,
                "explanation": explanation,
            },
        }

    def _lifestyle_insight(
        self,
        metric: str,
        data: dict,
    ) -> dict | None:

        if not data:
            return None

        value = self._safe_float(
            data.get(
                "value",
                0,
            )
        )

        readable_metric = (
            metric.replace(
                "_",
                " ",
            )
        )

        if metric == "sleep_duration":

            if value < 6:

                return {
                    "insight_type": "lifestyle",
                    "category": "sleep",
                    "severity": "moderate",
                    "priority": 2,
                    "confidence": 0.70,
                    "title": "Short sleep duration detected",
                    "message": (
                        f"The latest recorded sleep duration "
                        f"is {value:.1f} hours."
                    ),
                    "recommended_action": (
                        "Continue tracking sleep duration "
                        "and work toward a consistent sleep routine."
                    ),
                    "supporting_data": {
                        "metric": metric,
                        "value": value,
                        "unit": data.get(
                            "unit"
                        ),
                    },
                }

            if value >= 7:

                return {
                    "insight_type": "lifestyle",
                    "category": "sleep",
                    "severity": "low",
                    "priority": 1,
                    "confidence": 0.65,
                    "title": "Sleep duration is being tracked",
                    "message": (
                        f"The latest recorded sleep duration "
                        f"is {value:.1f} hours."
                    ),
                    "recommended_action": (
                        "Continue maintaining a consistent "
                        "sleep schedule."
                    ),
                    "supporting_data": {
                        "metric": metric,
                        "value": value,
                        "unit": data.get(
                            "unit"
                        ),
                    },
                }

        if metric == "steps":

            if value < 3000:

                return {
                    "insight_type": "lifestyle",
                    "category": "activity",
                    "severity": "moderate",
                    "priority": 2,
                    "confidence": 0.65,
                    "title": "Low recorded activity",
                    "message": (
                        f"The latest recorded step count "
                        f"is approximately {value:.0f} steps."
                    ),
                    "recommended_action": (
                        "Monitor daily activity and gradually "
                        "increase movement where appropriate."
                    ),
                    "supporting_data": {
                        "metric": metric,
                        "value": value,
                        "unit": data.get(
                            "unit"
                        ),
                    },
                }

        if metric == "water_intake":

            if value < 1.5:

                return {
                    "insight_type": "lifestyle",
                    "category": "hydration",
                    "severity": "low",
                    "priority": 1,
                    "confidence": 0.60,
                    "title": "Low recorded water intake",
                    "message": (
                        f"The latest recorded water intake "
                        f"is approximately {value:.2f} liters."
                    ),
                    "recommended_action": (
                        "Continue tracking fluid intake "
                        "throughout the day."
                    ),
                    "supporting_data": {
                        "metric": metric,
                        "value": value,
                        "unit": data.get(
                            "unit"
                        ),
                    },
                }

        return None

    def _state_insight(
        self,
        digital_twin: dict,
    ) -> dict | None:

        state = str(
            digital_twin.get(
                "state",
                "no_data",
            )
        )

        anomaly_score = self._safe_float(
            digital_twin.get(
                "anomaly_score",
                0,
            )
        )

        if state == "stable":

            return {
                "insight_type": "state",
                "category": "overall",
                "severity": "low",
                "priority": 1,
                "confidence": 0.70,
                "title": "Health pattern is currently stable",
                "message": (
                    "The available health-event data does not "
                    "show significant deviations from the "
                    "current personal baseline."
                ),
                "recommended_action": (
                    "Continue recording health data consistently."
                ),
                "supporting_data": {
                    "state": state,
                    "anomaly_score": anomaly_score,
                },
            }

        if state == "watch":

            return {
                "insight_type": "state",
                "category": "overall",
                "severity": "moderate",
                "priority": 2,
                "confidence": 0.75,
                "title": "Some health patterns need monitoring",
                "message": (
                    "The Digital Twin detected one or more "
                    "deviations from the user's historical "
                    "pattern."
                ),
                "recommended_action": (
                    "Continue monitoring the affected metrics "
                    "and record additional observations."
                ),
                "supporting_data": {
                    "state": state,
                    "anomaly_score": anomaly_score,
                },
            }

        if state == "elevated":

            return {
                "insight_type": "state",
                "category": "overall",
                "severity": "high",
                "priority": 3,
                "confidence": 0.80,
                "title": "Multiple deviations detected",
                "message": (
                    "The Digital Twin currently contains "
                    "multiple significant deviations from "
                    "the user's personal historical pattern."
                ),
                "recommended_action": (
                    "Review the affected measurements and "
                    "consider appropriate professional "
                    "medical guidance."
                ),
                "supporting_data": {
                    "state": state,
                    "anomaly_score": anomaly_score,
                },
            }

        if state == "attention_required":

            return {
                "insight_type": "state",
                "category": "overall",
                "severity": "high",
                "priority": 3,
                "confidence": 0.85,
                "title": "Multiple high-severity deviations",
                "message": (
                    "The available data contains multiple "
                    "high-severity deviations from the "
                    "personal historical pattern."
                ),
                "recommended_action": (
                    "Review the measurements promptly and "
                    "seek appropriate professional medical "
                    "advice when warranted."
                ),
                "supporting_data": {
                    "state": state,
                    "anomaly_score": anomaly_score,
                },
            }

        return None

    def generate_insights(
        self,
        digital_twin: dict,
        anomalies: pd.DataFrame | None = None,
    ) -> list[dict]:

        insights = []

        # Overall state insight.
        state_insight = (
            self._state_insight(
                digital_twin
            )
        )

        if state_insight is not None:
            insights.append(
                state_insight
            )

        # Digital Twin anomaly records.
        twin_anomalies = (
            digital_twin.get(
                "anomalies",
                [],
            )
        )

        for anomaly in twin_anomalies:

            insight = (
                self._anomaly_insight(
                    anomaly
                )
            )

            insights.append(
                insight
            )

        # Optional anomaly dataframe.
        if (
            anomalies is not None
            and not anomalies.empty
        ):

            detected = anomalies[
                anomalies["is_anomaly"] == True
            ]

            existing_event_ids = {
                insight[
                    "supporting_data"
                ].get(
                    "event_id"
                )
                for insight in insights
                if isinstance(
                    insight.get(
                        "supporting_data"
                    ),
                    dict,
                )
            }

            for _, row in detected.iterrows():

                event_id = int(
                    row["event_id"]
                )

                if event_id in existing_event_ids:
                    continue

                insight = (
                    self._anomaly_insight(
                        {
                            "event_type": row[
                                "event_type"
                            ],
                            "severity": row[
                                "severity"
                            ],
                            "confidence": row[
                                "confidence"
                            ],
                            "value": row[
                                "value"
                            ],
                            "explanation": row[
                                "explanation"
                            ],
                        }
                    )

                insight[
                    "supporting_data"
                ]["event_id"] = event_id

                insights.append(
                    insight
                )

        # Lifestyle insights.
        lifestyle = (
            digital_twin.get(
                "lifestyle",
                {},
            )
        )

        for metric, data in (
            lifestyle.items()
        ):

            insight = (
                self._lifestyle_insight(
                    metric,
                    data,
                )
            )

            if insight is not None:
                insights.append(
                    insight
                )

        # Sort by priority.
        insights.sort(
            key=lambda item: (
                item.get(
                    "priority",
                    0,
                ),
                item.get(
                    "confidence",
                    0,
                ),
            ),
            reverse=True,
        )

        # Add identifiers/timestamps.
        generated_at = (
            datetime.now(
                timezone.utc
            ).isoformat()
        )

        final_insights = []

        for index, insight in enumerate(
            insights[
                : self.maximum_insights
            ],
            start=1,
        ):

            final_insights.append(
                {
                    "insight_id": (
                        f"INS-{index:04d}"
                    ),
                    "generated_at": generated_at,
                    **insight,
                }
            )

        return final_insights

    def build_response(
        self,
        user_id: int,
        digital_twin: dict,
        insights: list[dict],
    ) -> dict:

        return {
            "user_id": user_id,
            "generated_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "digital_twin_state": digital_twin.get(
                "state",
                "no_data",
            ),
            "anomaly_score": digital_twin.get(
                "anomaly_score",
                0.0,
            ),
            "insight_count": len(
                insights
            ),
            "insights": insights,
        }

    def save_json(
        self,
        response: dict,
        output_file: Path,
    ) -> None:

        import json

        output_file.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with output_file.open(
            "w",
            encoding="utf-8",
        ) as file:

            json.dump(
                response,
                file,
                indent=2,
                ensure_ascii=False,
            )

    def save_csv(
        self,
        insights: list[dict],
        output_file: Path,
    ) -> None:

        output_file.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        rows = []

        for insight in insights:

            supporting_data = (
                insight.get(
                    "supporting_data",
                    {},
                )
            )

            rows.append(
                {
                    "insight_id": insight[
                        "insight_id"
                    ],
                    "generated_at": insight[
                        "generated_at"
                    ],
                    "insight_type": insight[
                        "insight_type"
                    ],
                    "category": insight[
                        "category"
                    ],
                    "severity": insight[
                        "severity"
                    ],
                    "priority": insight[
                        "priority"
                    ],
                    "confidence": insight[
                        "confidence"
                    ],
                    "title": insight[
                        "title"
                    ],
                    "message": insight[
                        "message"
                    ],
                    "recommended_action": insight[
                        "recommended_action"
                    ],
                    "event_type": (
                        supporting_data.get(
                            "event_type"
                        )
                    ),
                    "event_id": (
                        supporting_data.get(
                            "event_id"
                        )
                    ),
                }
            )

        pd.DataFrame(
            rows
        ).to_csv(
            output_file,
            index=False,
        )