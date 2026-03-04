import json
import unittest
from unittest.mock import patch

from src.tools.material_ops import get_material_slots


class MaterialSlotsTests(unittest.TestCase):
    def test_get_material_slots_builds_clean_error_json(self) -> None:
        with patch("src.tools.material_ops.client.send_command", return_value={"result": '{"error":"Object not found: Missing"}'}) as mocked_send:
            result = json.loads(get_material_slots("Missing"))

        maxscript = mocked_send.call_args.args[0]
        self.assertIn('"{\\"error\\":\\"Object not found: Missing\\"}"', maxscript)
        self.assertNotIn('{{\\\\"error\\\\":', maxscript)
        self.assertEqual(result["error"], "Object not found: Missing")

    def test_get_material_slots_compacts_payload(self) -> None:
        payload = {
            "name": "Mat",
            "class": "ai_standard_surface",
            "subMaterialIndex": 0,
            "inspectedCount": 5,
            "counts": {"map": 1, "color": 1, "numeric": 1, "bool": 1, "other": 1},
            "mapSlots": ["base_color_shader"],
            "colorSlots": ["base_color"],
            "numericSlots": ["specular_roughness"],
            "boolSlots": ["thin_walled"],
            "otherSlots": ["name"],
        }
        with patch("src.tools.material_ops.client.send_command", return_value={"result": json.dumps(payload)}):
            result = json.loads(get_material_slots("AITest_Box", slot_scope="all"))

        self.assertEqual(result["class"], "ai_standard_surface")
        self.assertEqual(result["mapSlots"], ["base_color_shader"])
        self.assertEqual(result["numericSlots"], ["specular_roughness"])
        self.assertIn("hints", result)


if __name__ == "__main__":
    unittest.main()
