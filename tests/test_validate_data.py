from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from validate_data import validate_against_previous, validate_payload  # noqa: E402


def valid_payload() -> dict:
    return {
        "lastUpdated": "2026-09-21T12:00:00+00:00",
        "brands": [
            {
                "name": "Zimmermann",
                "items": [
                    {
                        "id": "everly",
                        "name": "Zimmermann Everly Dress",
                        "cheapestPrice": 250.0,
                        "offers": [
                            {
                                "name": "Saks Fifth Avenue",
                                "price": 250.0,
                                "originalPrice": 500.0,
                                "url": "https://example.com/everly",
                                "sourceCategory": "retail",
                            }
                        ],
                    }
                ],
            }
        ],
    }


class DataValidationTests(unittest.TestCase):
    def test_valid_payload_passes(self) -> None:
        self.assertEqual(validate_payload(valid_payload()), [])

    def test_duplicate_item_and_bad_offer_are_rejected(self) -> None:
        payload = valid_payload()
        duplicate = dict(payload["brands"][0]["items"][0])
        duplicate["offers"] = [dict(duplicate["offers"][0])]
        duplicate["offers"][0]["price"] = -1
        duplicate["offers"][0]["url"] = "javascript:alert(1)"
        payload["brands"][0]["items"].append(duplicate)

        errors = validate_payload(payload)

        self.assertTrue(any("duplicated" in error for error in errors))
        self.assertTrue(any("positive finite" in error for error in errors))
        self.assertTrue(any("absolute HTTP(S)" in error for error in errors))

    def test_large_item_count_drop_is_rejected(self) -> None:
        previous = valid_payload()
        previous["brands"][0]["items"] *= 10
        current = valid_payload()
        current["brands"][0]["items"] = []

        errors = validate_against_previous(current, previous)

        self.assertEqual(len(errors), 1)
        self.assertIn("item count dropped", errors[0])


if __name__ == "__main__":
    unittest.main()
