from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import fetch_serpapi  # noqa: E402
from observability import CollectionMetrics  # noqa: E402


class NormalizationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.brand = fetch_serpapi.default_brand_config()

    def test_parse_price_handles_currency_and_commas(self) -> None:
        self.assertEqual(fetch_serpapi.parse_price("$1,299.99"), 1299.99)
        self.assertIsNone(fetch_serpapi.parse_price(None))

    def test_normalize_title_removes_brand_and_filler_words(self) -> None:
        normalized = fetch_serpapi.normalize_title(
            "Zimmermann Women's Everley Floral Midi Dress", self.brand
        )
        self.assertEqual(normalized, "everley floral midi dress")

    def test_item_name_is_canonicalized(self) -> None:
        name = fetch_serpapi.normalize_item_name(
            "Zimmermann Women's Cream Everley Dress - Saks Fifth Avenue", self.brand
        )
        self.assertEqual(name, "Zimmermann Everley Dress")


class MatchingAndDedupeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.brand = fetch_serpapi.default_brand_config()

    def test_find_group_key_matches_similar_titles(self) -> None:
        grouped = {
            "everly-midi": {
                "normalizedTitle": "everly floral midi dress",
                "modelKey": "everly",
            }
        }
        result = fetch_serpapi.find_group_key(
            grouped,
            "everly floral midi dresses",
            "everly",
            "different-slug",
        )
        self.assertEqual(result, "everly-midi")

    def test_dedupe_offers_keeps_better_url_and_sorts_by_price(self) -> None:
        common = {
            "original_price": 500.0,
            "image": None,
            "updated_at": "2026-09-21T00:00:00+00:00",
            "source_category": "retail",
        }
        offers = [
            fetch_serpapi.StoreOffer(name="Saks", price=300.0, url="https://x.co/a", **common),
            fetch_serpapi.StoreOffer(
                name="Saks", price=300.0, url="https://example.com/products/everly", **common
            ),
            fetch_serpapi.StoreOffer(name="Nordstrom", price=250.0, url="https://n.example/a", **common),
        ]

        deduped = fetch_serpapi.dedupe_offers(offers, self.brand)

        self.assertEqual(len(deduped), 2)
        self.assertEqual(deduped[0].price, 250.0)
        self.assertEqual(deduped[1].url, "https://example.com/products/everly")


class ApiFailureTests(unittest.TestCase):
    def test_bad_serpapi_response_fails_closed(self) -> None:
        metrics = CollectionMetrics()
        with (
            patch.object(fetch_serpapi, "load_cached_results", return_value=None),
            patch.object(
                fetch_serpapi,
                "fetch_shopping_results_serpapi",
                side_effect=RuntimeError("503 upstream unavailable"),
            ),
        ):
            results = fetch_serpapi.fetch_shopping_results("unique test query", "secret", metrics)

        self.assertEqual(results, [])
        self.assertEqual(metrics.api_errors, 1)


if __name__ == "__main__":
    unittest.main()
