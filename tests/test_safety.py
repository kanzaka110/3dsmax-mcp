"""Tests for the safety gate module."""

import unittest

from src.safety import RiskLevel, classify_risk, format_safety_warning, wrap_with_safety


class TestClassifyRisk(unittest.TestCase):
    def test_delete_objects_is_dangerous(self) -> None:
        risk = classify_risk("delete_objects")
        self.assertEqual(risk.level, RiskLevel.DANGEROUS)
        self.assertIn("remove", risk.reason.lower())

    def test_execute_maxscript_is_dangerous(self) -> None:
        risk = classify_risk("execute_maxscript")
        self.assertEqual(risk.level, RiskLevel.DANGEROUS)

    def test_manage_scene_reset_is_dangerous(self) -> None:
        risk = classify_risk("manage_scene", action="reset")
        self.assertEqual(risk.level, RiskLevel.DANGEROUS)
        self.assertIn("reset", risk.reason.lower())

    def test_manage_scene_hold_is_safe(self) -> None:
        risk = classify_risk("manage_scene", action="hold")
        self.assertEqual(risk.level, RiskLevel.SAFE)

    def test_manage_scene_info_is_safe(self) -> None:
        risk = classify_risk("manage_scene", action="info")
        self.assertEqual(risk.level, RiskLevel.SAFE)

    def test_manage_scene_save_is_caution(self) -> None:
        risk = classify_risk("manage_scene", action="save")
        self.assertEqual(risk.level, RiskLevel.CAUTION)

    def test_unknown_tool_is_safe(self) -> None:
        risk = classify_risk("get_scene_info")
        self.assertEqual(risk.level, RiskLevel.SAFE)


class TestFormatSafetyWarning(unittest.TestCase):
    def test_safe_returns_empty(self) -> None:
        risk = classify_risk("get_scene_info")
        self.assertEqual(format_safety_warning(risk), "")

    def test_dangerous_includes_reason_and_suggestion(self) -> None:
        risk = classify_risk("delete_objects")
        warning = format_safety_warning(risk)
        self.assertIn("DANGEROUS", warning)
        self.assertIn("hold", warning.lower())


class TestWrapWithSafety(unittest.TestCase):
    def test_safe_tool_returns_result_unchanged(self) -> None:
        result = wrap_with_safety("get_scene_info", "some data")
        self.assertEqual(result, "some data")

    def test_dangerous_tool_prepends_warning(self) -> None:
        result = wrap_with_safety("delete_objects", "Deleted: Box01")
        self.assertTrue(result.startswith("WARNING:"))
        self.assertIn("Deleted: Box01", result)

    def test_caution_tool_returns_result_unchanged(self) -> None:
        result = wrap_with_safety("manage_scene", "Saved: test.max", action="save")
        self.assertEqual(result, "Saved: test.max")

    def test_conditional_dangerous_prepends_warning(self) -> None:
        result = wrap_with_safety("manage_scene", "Scene reset", action="reset")
        self.assertTrue(result.startswith("WARNING:"))
        self.assertIn("Scene reset", result)

    def test_conditional_safe_returns_unchanged(self) -> None:
        result = wrap_with_safety("manage_scene", "Hold ok", action="hold")
        self.assertEqual(result, "Hold ok")


if __name__ == "__main__":
    unittest.main()
