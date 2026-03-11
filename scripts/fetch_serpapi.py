from __future__ import annotations

import json
import os
import sys
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from utils import load_env_file, load_json, save_json, slugify


PROJECT_ROOT = Path(__file__).resolve().parent.parent
WATCHLIST_PATH = PROJECT_ROOT / "config" / "watchlist.json"
DEALS_PATH = PROJECT_ROOT / "data" / "deals.json"
CACHE_DIR = PROJECT_ROOT / "data" / "cache"
ENV_PATH = PROJECT_ROOT / ".env"
SERPAPI_URL = "https://serpapi.com/search.json"
CACHE_TTL_HOURS = 24
REQUEST_TIMEOUT_SECONDS = 20
RATE_LIMIT_DELAY_SECONDS = 1


@dataclass
class StoreOffer:
    name: str
    price: float
    original_price: float
    url: str
    image: str | None
    updated_at: str


def load_cached_results(query: str) -> list[dict[str, Any]] | None:
    cache_file = CACHE_DIR / f"{slugify(query)}.json"

    if not cache_file.exists():
        return None

    age = datetime.now() - datetime.fromtimestamp(cache_file.stat().st_mtime)
    if age.total_seconds() > CACHE_TTL_HOURS * 3600:
        return None

    return load_json(cache_file)


def fetch_shopping_results(query: str, api_key: str) -> list[dict[str, Any]]:
    cached = load_cached_results(query)
    if cached is not None:
        return cached

    params = {
        "engine": "google_shopping",
        "q": query,
        "api_key": api_key,
        "gl": "us",
        "hl": "en"
    }
    url = f"{SERPAPI_URL}?{urllib.parse.urlencode(params)}"

    with urllib.request.urlopen(url, timeout=REQUEST_TIMEOUT_SECONDS) as response:
        payload = json.load(response)

    if "shopping_results" not in payload:
        return []

    results = payload["shopping_results"]
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    save_json(CACHE_DIR / f"{slugify(query)}.json", results)
    return results


def parse_price(raw_value: str | float | int | None) -> float | None:
    if raw_value is None:
        return None

    if isinstance(raw_value, (float, int)):
        return float(raw_value)

    cleaned = "".join(character for character in str(raw_value) if character.isdigit() or character == ".")
    return float(cleaned) if cleaned else None


def map_offers(results: list[dict[str, Any]], timestamp: str) -> list[StoreOffer]:
    offers: list[StoreOffer] = []

    for result in results[:5]:
        current_price = parse_price(result.get("price"))
        original_price = parse_price(result.get("extracted_old_price")) or current_price

        if current_price is None:
            continue

        offers.append(
            StoreOffer(
                name=result.get("source", "Unknown store"),
                price=current_price,
                original_price=original_price or current_price,
                url=result.get("product_link") or result.get("link") or "",
                image=result.get("thumbnail") or result.get("serpapi_thumbnail"),
                updated_at=timestamp
            )
        )

    return offers


def merge_with_existing(item_name: str, brand_name: str, offers: list[StoreOffer], existing: dict[str, Any]) -> dict[str, Any]:
    item_id = slugify(item_name)
    previous_items = {
        item["id"]: item
        for brand in existing.get("brands", [])
        if brand["name"] == brand_name
        for item in brand.get("items", [])
    }
    previous = previous_items.get(item_id, {})
    sorted_offers = sorted(offers, key=lambda offer: offer.price)
    best_offer = sorted_offers[0]
    history = previous.get("history", [])

    if not history or history[-1]["price"] != best_offer.price:
        history.append({
            "date": datetime.fromisoformat(best_offer.updated_at).date().isoformat(),
            "price": best_offer.price
        })

    return {
        "id": item_id,
        "name": item_name,
        "silhouette": previous.get("silhouette", "Dress"),
        "material": previous.get("material", "Unknown"),
        "imageUrl": previous.get("imageUrl") or best_offer.image,
        "stores": [
            {
                "name": offer.name,
                "price": offer.price,
                "originalPrice": offer.original_price,
                "url": offer.url,
                "imageUrl": offer.image,
                "updatedAt": offer.updated_at
            }
            for offer in sorted_offers
        ],
        "history": history
    }


def collect() -> dict[str, Any]:
    load_env_file(ENV_PATH)
    api_key = os.getenv("SERPAPI_API_KEY")

    if not api_key:
        raise RuntimeError("SERPAPI_API_KEY is not set.")

    watchlist = load_json(WATCHLIST_PATH)
    existing = load_json(DEALS_PATH)
    timestamp = datetime.now().astimezone().isoformat(timespec="seconds")
    brands: list[dict[str, Any]] = []

    for brand in watchlist["brands"]:
        items: list[dict[str, Any]] = []
        for query in brand["queries"]:
            results = fetch_shopping_results(query, api_key)
            time.sleep(RATE_LIMIT_DELAY_SECONDS)
            offers = map_offers(results, timestamp)
            if not offers:
                continue

            items.append(merge_with_existing(query, brand["name"], offers, existing))

        brands.append({
            "name": brand["name"],
            "items": items
        })

    return {
        "lastUpdated": timestamp,
        "currency": watchlist.get("currency", "USD"),
        "brands": brands
    }


def main() -> int:
    try:
        payload = collect()
        save_json(DEALS_PATH, payload)
        print(f"Updated {DEALS_PATH}")
        return 0
    except Exception as error:
        print(f"Collection failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
