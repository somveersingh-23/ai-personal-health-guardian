import math
import unittest
from dataclasses import FrozenInstanceError

from ml.safety import SafetyAction, SafetyDecision, SafetyEngine, SafetyInput


class SafetyEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = SafetyEngine()

    def test_no_deviation_is_normal(self) -> None:
        result = self.engine.evaluate(
            SafetyInput(deviation_score=0, confidence=0.9, signal_quality=0.9)
        )
        self.assertEqual(result.action, SafetyAction.NORMAL)

    def test_small_deviation_is_observed(self) -> None:
        result = self.engine.evaluate(
            SafetyInput(deviation_score=0.8, confidence=0.8, signal_quality=0.8)
        )
        self.assertEqual(result.action, SafetyAction.OBSERVE)

    def test_low_quality_requires_remeasurement(self) -> None:
        result = self.engine.evaluate(
            SafetyInput(deviation_score=3.0, confidence=0.9, signal_quality=0.3)
        )
        self.assertEqual(result.action, SafetyAction.RE_MEASURE)

    def test_moderate_deviation_allows_self_care(self) -> None:
        result = self.engine.evaluate(
            SafetyInput(deviation_score=1.8, confidence=0.8, signal_quality=0.8)
        )
        self.assertEqual(result.action, SafetyAction.SELF_CARE)

    def test_high_deviation_requests_caregiver_review(self) -> None:
        result = self.engine.evaluate(
            SafetyInput(deviation_score=2.8, confidence=0.8, signal_quality=0.8)
        )
        self.assertEqual(result.action, SafetyAction.CAREGIVER_ALERT)
        self.assertTrue(result.requires_human_confirmation)

    def test_high_confidence_critical_flag_escalates(self) -> None:
        result = self.engine.evaluate(
            SafetyInput.from_evidence(
                deviation_score=2.0,
                confidence=0.9,
                signal_quality=0.9,
                critical_flags=["validated_critical_pattern"],
            )
        )
        self.assertEqual(result.action, SafetyAction.EMERGENCY_ESCALATION)

    def test_confirmed_severe_symptoms_override_low_sensor_quality(self) -> None:
        result = self.engine.evaluate(
            SafetyInput(
                deviation_score=0,
                confidence=0.1,
                signal_quality=0.1,
                user_confirmed_severe_symptoms=True,
            )
        )
        self.assertEqual(result.action, SafetyAction.EMERGENCY_ESCALATION)

    def test_invalid_confidence_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "confidence must be between 0 and 1"):
            SafetyInput(deviation_score=1, confidence=1.1, signal_quality=0.8)

    def test_all_action_values_are_stable_api_strings(self) -> None:
        self.assertEqual(
            {action.value for action in SafetyAction},
            {
                "normal",
                "observe",
                "re_measure",
                "self_care",
                "caregiver_alert",
                "emergency_escalation",
            },
        )

    def test_from_evidence_converts_iterables_to_immutable_tuples(self) -> None:
        result = SafetyInput.from_evidence(
            deviation_score=1,
            confidence=0.8,
            signal_quality=0.8,
            evidence=(item for item in ["sleep decreased", "HRV decreased"]),
            critical_flags=["flag"],
        )
        self.assertEqual(result.evidence, ("sleep decreased", "HRV decreased"))
        self.assertEqual(result.critical_flags, ("flag",))

    def test_inputs_and_decisions_are_immutable(self) -> None:
        data = SafetyInput(0, 1, 1)
        decision = self.engine.evaluate(data)
        with self.assertRaises(FrozenInstanceError):
            data.confidence = 0.5
        with self.assertRaises(FrozenInstanceError):
            decision.action = SafetyAction.OBSERVE

    def test_confidence_and_quality_accept_closed_interval_boundaries(self) -> None:
        SafetyInput(deviation_score=0, confidence=0, signal_quality=1)
        SafetyInput(deviation_score=0, confidence=1, signal_quality=0)

    def test_negative_deviation_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "deviation_score must be non-negative"):
            SafetyInput(deviation_score=-0.01, confidence=0.8, signal_quality=0.8)

    def test_invalid_signal_quality_is_rejected(self) -> None:
        for value in (-0.01, 1.01):
            with self.subTest(value=value):
                with self.assertRaisesRegex(
                    ValueError, "signal_quality must be between 0 and 1"
                ):
                    SafetyInput(deviation_score=1, confidence=0.8, signal_quality=value)

    def test_non_finite_numbers_are_rejected(self) -> None:
        for field in ("deviation_score", "confidence", "signal_quality"):
            for value in (math.nan, math.inf, -math.inf):
                values = {
                    "deviation_score": 1.0,
                    "confidence": 0.8,
                    "signal_quality": 0.8,
                }
                values[field] = value
                with self.subTest(field=field, value=value):
                    with self.assertRaisesRegex(ValueError, f"{field} must be a finite number"):
                        SafetyInput(**values)

    def test_non_numeric_and_boolean_values_are_rejected(self) -> None:
        for field in ("deviation_score", "confidence", "signal_quality"):
            for value in ("0.8", None, True):
                values = {
                    "deviation_score": 1.0,
                    "confidence": 0.8,
                    "signal_quality": 0.8,
                }
                values[field] = value
                with self.subTest(field=field, value=value):
                    with self.assertRaisesRegex(ValueError, f"{field} must be a finite number"):
                        SafetyInput(**values)

    def test_exact_quality_and_confidence_minimums_are_usable(self) -> None:
        result = self.engine.evaluate(
            SafetyInput(
                deviation_score=SafetyEngine.MODERATE_DEVIATION,
                confidence=SafetyEngine.MIN_USABLE_CONFIDENCE,
                signal_quality=SafetyEngine.MIN_USABLE_QUALITY,
            )
        )
        self.assertEqual(result.action, SafetyAction.SELF_CARE)

    def test_value_just_below_each_usability_threshold_requires_remeasurement(self) -> None:
        cases = (
            (SafetyEngine.MIN_USABLE_CONFIDENCE - 0.001, 0.9),
            (0.9, SafetyEngine.MIN_USABLE_QUALITY - 0.001),
        )
        for confidence, quality in cases:
            with self.subTest(confidence=confidence, quality=quality):
                result = self.engine.evaluate(
                    SafetyInput(3.0, confidence, quality)
                )
                self.assertEqual(result.action, SafetyAction.RE_MEASURE)

    def test_exact_deviation_thresholds_select_expected_actions(self) -> None:
        cases = (
            (0.0, SafetyAction.NORMAL),
            (0.001, SafetyAction.OBSERVE),
            (SafetyEngine.MODERATE_DEVIATION, SafetyAction.SELF_CARE),
            (SafetyEngine.HIGH_DEVIATION, SafetyAction.CAREGIVER_ALERT),
        )
        for score, action in cases:
            with self.subTest(score=score):
                result = self.engine.evaluate(SafetyInput(score, 0.8, 0.8))
                self.assertEqual(result.action, action)

    def test_critical_flag_at_exact_high_confidence_escalates(self) -> None:
        result = self.engine.evaluate(
            SafetyInput.from_evidence(
                deviation_score=0,
                confidence=SafetyEngine.HIGH_CONFIDENCE,
                signal_quality=SafetyEngine.MIN_USABLE_QUALITY,
                critical_flags=["validated flag"],
            )
        )
        self.assertEqual(result.action, SafetyAction.EMERGENCY_ESCALATION)

    def test_critical_flag_below_high_confidence_requests_caregiver(self) -> None:
        result = self.engine.evaluate(
            SafetyInput.from_evidence(
                deviation_score=0,
                confidence=SafetyEngine.HIGH_CONFIDENCE - 0.001,
                signal_quality=0.8,
                critical_flags=["validated flag"],
            )
        )
        self.assertEqual(result.action, SafetyAction.CAREGIVER_ALERT)

    def test_low_quality_takes_priority_over_unconfirmed_critical_flag(self) -> None:
        result = self.engine.evaluate(
            SafetyInput.from_evidence(
                deviation_score=3,
                confidence=0.9,
                signal_quality=0.2,
                critical_flags=["unreliable flag"],
            )
        )
        self.assertEqual(result.action, SafetyAction.RE_MEASURE)

    def test_evidence_and_flags_are_trimmed_and_blank_items_removed(self) -> None:
        result = self.engine.evaluate(
            SafetyInput.from_evidence(
                deviation_score=3,
                confidence=0.8,
                signal_quality=0.8,
                evidence=[" sleep decreased ", "", "   "],
                critical_flags=[" warning ", ""],
            )
        )
        self.assertEqual(result.evidence, ("sleep decreased", "warning"))

    def test_blank_critical_flags_do_not_trigger_alert(self) -> None:
        result = self.engine.evaluate(
            SafetyInput.from_evidence(
                deviation_score=0,
                confidence=0.9,
                signal_quality=0.9,
                critical_flags=["", "   "],
            )
        )
        self.assertEqual(result.action, SafetyAction.NORMAL)

    def test_every_decision_contains_non_diagnosis_disclaimer_and_reason(self) -> None:
        cases = (
            SafetyInput(0, 0.9, 0.9),
            SafetyInput(0.5, 0.9, 0.9),
            SafetyInput(2.0, 0.9, 0.9),
            SafetyInput(3.0, 0.9, 0.9),
            SafetyInput(3.0, 0.2, 0.9),
            SafetyInput(0, 0.1, 0.1, user_confirmed_severe_symptoms=True),
        )
        for data in cases:
            with self.subTest(data=data):
                result = self.engine.evaluate(data)
                self.assertTrue(result.reason)
                self.assertIn("not a medical diagnosis", result.disclaimer)

    def test_human_confirmation_only_for_human_escalation_actions(self) -> None:
        cases = (
            (SafetyInput(0, 0.9, 0.9), False),
            (SafetyInput(0.5, 0.9, 0.9), False),
            (SafetyInput(2.0, 0.9, 0.9), False),
            (SafetyInput(3.0, 0.9, 0.9), True),
            (SafetyInput(3.0, 0.2, 0.9), False),
            (SafetyInput(0, 0.1, 0.1, user_confirmed_severe_symptoms=True), True),
        )
        for data, expected in cases:
            with self.subTest(data=data):
                self.assertEqual(
                    self.engine.evaluate(data).requires_human_confirmation,
                    expected,
                )

    def test_decision_can_be_constructed_for_downstream_contract(self) -> None:
        decision = SafetyDecision(
            action=SafetyAction.OBSERVE,
            reason="Monitor the change.",
            evidence=("sleep decreased",),
            requires_human_confirmation=False,
        )
        self.assertEqual(decision.action.value, "observe")
        self.assertEqual(decision.evidence, ("sleep decreased",))


if __name__ == "__main__":
    unittest.main()
