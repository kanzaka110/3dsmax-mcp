"""Tests for MockMaxClient itself — validates the mock infrastructure works correctly."""

import unittest

from tests.mock_client import MockMaxClient


class TestMockClientResponses(unittest.TestCase):
    def test_default_response_returns_ok(self) -> None:
        mock = MockMaxClient()
        response = mock.send_command("anything")
        self.assertTrue(response["success"])
        self.assertEqual(response["result"], "ok")
        self.assertIn("requestId", response)
        self.assertIn("meta", response)

    def test_add_response_by_cmd_type(self) -> None:
        mock = MockMaxClient()
        mock.add_response("native:ping", {"pong": True, "server": "3dsmax-mcp"})

        response = mock.send_command("", cmd_type="native:ping")
        self.assertTrue(response["pong"])
        self.assertEqual(response["server"], "3dsmax-mcp")

    def test_add_response_with_pattern_matching(self) -> None:
        mock = MockMaxClient()
        mock.add_response("maxscript", "Box01 created", pattern=r"Box")
        mock.add_response("maxscript", "Sphere01 created", pattern=r"Sphere")

        r1 = mock.send_command("create Box name:TestBox")
        self.assertEqual(r1["result"], "Box01 created")

        r2 = mock.send_command("create Sphere radius:25")
        self.assertEqual(r2["result"], "Sphere01 created")

    def test_string_shorthand_for_result(self) -> None:
        mock = MockMaxClient()
        mock.add_response("maxscript", "hello world")
        response = mock.send_command("test")
        self.assertEqual(response["result"], "hello world")

    def test_last_rule_wins_on_conflict(self) -> None:
        mock = MockMaxClient()
        mock.add_response("maxscript", "first")
        mock.add_response("maxscript", "second")
        response = mock.send_command("test")
        self.assertEqual(response["result"], "second")

    def test_unmatched_cmd_type_falls_back_to_default(self) -> None:
        mock = MockMaxClient()
        mock.add_response("native:ping", "pong")
        response = mock.send_command("test", cmd_type="maxscript")
        self.assertEqual(response["result"], "ok")


class TestMockClientCallHistory(unittest.TestCase):
    def test_records_all_calls(self) -> None:
        mock = MockMaxClient()
        mock.send_command("cmd1", cmd_type="maxscript")
        mock.send_command("cmd2", cmd_type="native:ping")
        self.assertEqual(mock.call_count, 2)

    def test_last_call_returns_most_recent(self) -> None:
        mock = MockMaxClient()
        mock.send_command("first")
        mock.send_command("second")
        self.assertEqual(mock.last_call().command, "second")

    def test_calls_for_filters_by_cmd_type(self) -> None:
        mock = MockMaxClient()
        mock.send_command("a", cmd_type="maxscript")
        mock.send_command("b", cmd_type="native:ping")
        mock.send_command("c", cmd_type="maxscript")
        self.assertEqual(len(mock.calls_for("maxscript")), 2)
        self.assertEqual(len(mock.calls_for("native:ping")), 1)

    def test_reset_history_clears_records(self) -> None:
        mock = MockMaxClient()
        mock.send_command("test")
        mock.reset_history()
        self.assertEqual(mock.call_count, 0)


class TestMockClientNativeToggle(unittest.TestCase):
    def test_native_available_defaults_to_true(self) -> None:
        mock = MockMaxClient()
        self.assertTrue(mock.native_available)

    def test_native_available_can_be_disabled(self) -> None:
        mock = MockMaxClient(native_available=False)
        self.assertFalse(mock.native_available)

    def test_native_available_can_be_toggled(self) -> None:
        mock = MockMaxClient()
        mock.native_available = False
        self.assertFalse(mock.native_available)


class TestMockClientPatchHelper(unittest.TestCase):
    def test_patch_client_replaces_module_client(self) -> None:
        from unittest.mock import patch as _patch
        from src.tools import objects as objects_mod

        mock = MockMaxClient()
        mock.add_response("native:delete_objects", "Deleted: Box01")

        with _patch.object(objects_mod, "client", mock):
            result = objects_mod.delete_objects(["Box01"])
            # Result includes safety warning for dangerous tools
            self.assertIn("Deleted: Box01", result)

        self.assertEqual(mock.call_count, 1)
        self.assertEqual(mock.last_call().cmd_type, "native:delete_objects")


if __name__ == "__main__":
    unittest.main()
