"""
Parse tests for `SENSOR_MODEL_IDS` string format (no device).
Run: uv run python -m unittest tests.test_sensors_toml
"""
import importlib
import os
import sys
import unittest

FIRMWARE = os.path.join(os.path.dirname(__file__), "..", "firmware")
FIRMWARE = os.path.abspath(FIRMWARE)
if FIRMWARE not in sys.path:
    sys.path.insert(0, FIRMWARE)

ids = importlib.import_module("sensors_toml_ids")


class TestParseCommaSeparatedInts(unittest.TestCase):
    def test_empty_and_none(self):
        self.assertEqual(ids.parse_comma_separated_ints(None), ([], []))
        self.assertEqual(ids.parse_comma_separated_ints(""), ([], []))
        self.assertEqual(ids.parse_comma_separated_ints("   "), ([], []))

    def test_commas(self):
        self.assertEqual(
            ids.parse_comma_separated_ints("1,2,3"),
            ([1, 2, 3], []),
        )
        self.assertEqual(
            ids.parse_comma_separated_ints("1, 2 , 3"),
            ([1, 2, 3], []),
        )

    def test_hex(self):
        self.assertEqual(
            ids.parse_comma_separated_ints("0xa, 10"),
            ([10, 10], []),
        )

    def test_invalid_tokens(self):
        v, bad = ids.parse_comma_separated_ints("1,foo,3")
        self.assertEqual(v, [1, 3])
        self.assertEqual(bad, ["foo"])


if __name__ == "__main__":
    unittest.main()
