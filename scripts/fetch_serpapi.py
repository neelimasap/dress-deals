from __future__ import annotations

import json
import os
import re
import sys
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from utils import load_env_file, load_json, save_json, slugify


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEALS_PATH = PROJECT_ROOT / "data" / "deals.json"
CACHE_DIR = PROJECT_ROOT / "data" / "cache"
ENV_PATH = PROJECT_ROOT / ".env"
SERPAPI_URL = "https://serpapi.com/search.json"
CACHE_TTL_HOURS = 24
REQUEST_TIMEOUT_SECONDS = 20
BRAND_NAME = "Zimmermann"
BRAND_QUERY = "Zimmermann dress"
YEAR_PATTERN = re.compile(r"\b(20\d{2})\b")
DRESS_PATTERN = re.compile(r"\b(dress|gown|minidress|maxidress|mididress|shirtdress)\b", re.IGNORECASE)
FILLER_PATTERN = re.compile(r"\b(by|womens|women|woman|size|new)\b", re.IGNORECASE)
FUZZY_MATCH_THRESHOLD = 0.9
NOISE_TITLE_PATTERN = re.compile(
    r"\b(nwt|kids|closet|preowned|pre-owned|used|affare del giorno|sz\b|op\b)\b",
    re.IGNORECASE,
)
NOISE_SOURCE_PATTERN = re.compile(
    r"\b(poshmark|ebay|born into money|bundesamt|naked pear)\b",
    re.IGNORECASE,
)
GENERIC_WORDS = {
    "dress",
    "gown",
    "midi",
    "mini",
    "maxi",
    "linen",
    "silk",
    "cotton",
    "floral",
    "print",
    "pattern",
    "wrap",
    "drape",
    "picnic",
    "long",
    "slip",
    "trim",
    "button",
    "fitted",
    "mermaid",
    "casual",
    "voile",
    "pleated",
    "tiered",
    "knot",
}
TOKEN_ALIASES = {
    "everley": "everly",
}


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


def fetch_shopping_results(query: str, api_key: str | None) -> list[dict[str, Any]]:
    cached = load_cached_results(query)
    if cached is not None:
        return cached

    if not api_key:
        raise RuntimeError("SERPAPI_API_KEY is not set and no fresh cache is available.")

    params = {
        "engine": "google_shopping",
        "q": query,
        "api_key": api_key,
        "gl": "us",
        "hl": "en",
    }
    url = f"{SERPAPI_URL}?{urllib.parse.urlencode(params)}"

    with urllib.request.urlopen(url, timeout=REQUEST_TIMEOUT_SECONDS) as response:
        payload = json.load(response)

    results = payload.get("shopping_results", [])
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


def get_text_blob(result: dict[str, Any]) -> str:
    extensions = " ".join(str(entry) for entry in result.get("extensions", []))
    fields = [
        result.get("title", ""),
        result.get("snippet", ""),
        extensions,
    ]
    return " ".join(fields)


def extract_release_year(result: dict[str, Any], now: datetime) -> int | None:
    years = {
        int(match)
        for match in YEAR_PATTERN.findall(get_text_blob(result))
        if 2000 <= int(match) <= now.year + 1
    }
    if not years:
        return None

    return max(years)


def looks_like_zimmermann_dress(result: dict[str, Any]) -> bool:
    title = str(result.get("title", ""))
    title_lower = title.lower()
    return BRAND_NAME.lower() in title_lower and bool(DRESS_PATTERN.search(title_lower))


def looks_like_noise(result: dict[str, Any]) -> bool:
    title = str(result.get("title", ""))
    source = str(result.get("source", ""))
    return bool(NOISE_TITLE_PATTERN.search(title) or NOISE_SOURCE_PATTERN.search(source))


def normalize_item_name(title: str) -> str:
    name = title.strip()
    name = re.sub(rf"^{BRAND_NAME}\s*[,.-]?\s*", "", name, flags=re.IGNORECASE)
    name = re.sub(r"^women'?s\s+", "", name, flags=re.IGNORECASE)
    name = re.split(r"\s+\|\s+|\s+-\s+", name, maxsplit=1)[0]
    name = re.sub(r",\s*women.*$", "", name, flags=re.IGNORECASE)
    name = re.sub(r",\s*dresses.*$", "", name, flags=re.IGNORECASE)
    name = re.sub(r"\s+in\s+[a-z].*$", "", name, flags=re.IGNORECASE)
    name = re.sub(r"\s+size\s+.*$", "", name, flags=re.IGNORECASE)
    name = re.sub(r"\s+", " ", name).strip(" ,.-")
    if not name.lower().startswith(BRAND_NAME.lower()):
        name = f"{BRAND_NAME} {name}"
    return name


def normalize_title(title: str) -> str:
    cleaned = title.lower().replace(BRAND_NAME.lower(), " ")
    cleaned = FILLER_PATTERN.sub(" ", cleaned)
    cleaned = re.sub(r"[^a-z0-9 ]", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def product_slug(normalized_title: str) -> str:
    words = [word for word in normalized_title.split() if word not in {"dress", "gown"}]
    important = words[:3] or normalized_title.split()[:3]
    return "-".join(important)


def canonical_tokens(normalized_title: str) -> list[str]:
    tokens: list[str] = []
    for raw_token in normalized_title.split():
        token = TOKEN_ALIASES.get(raw_token, raw_token)
        if token.isdigit():
            continue
        if len(token) <= 1:
            continue
        tokens.append(token)
    return tokens


def canonical_model_key(normalized_title: str) -> str:
    tokens = canonical_tokens(normalized_title)
    if not tokens:
        return ""

    for token in tokens:
        if token not in GENERIC_WORDS:
            return token

    return tokens[0]


def similarity(left: str, right: str) -> float:
    return SequenceMatcher(None, left, right).ratio()


def find_group_key(grouped: dict[str, dict[str, Any]], normalized_title: str, model_key: str, slug: str) -> str | None:
    if model_key and model_key in grouped:
        return model_key
    if slug in grouped:
        return slug

    for existing_slug, entry in grouped.items():
        if similarity(normalized_title, entry["normalizedTitle"]) >= FUZZY_MATCH_THRESHOLD:
            return existing_slug

    return None


def build_offer(result: dict[str, Any], timestamp: str) -> StoreOffer | None:
    current_price = (
        parse_price(result.get("extracted_price"))
        or parse_price(result.get("price"))
    )
    original_price = (
        parse_price(result.get("extracted_old_price"))
        or parse_price(result.get("old_price"))
        or current_price
    )

    if current_price is None:
        return None

    return StoreOffer(
        name=str(result.get("source") or "Unknown store"),
        price=current_price,
        original_price=original_price or current_price,
        url=str(result.get("product_link") or result.get("link") or ""),
        image=result.get("thumbnail") or result.get("serpapi_thumbnail"),
        updated_at=timestamp,
    )


def load_previous_items() -> dict[str, dict[str, Any]]:
    if not DEALS_PATH.exists():
        return {}

    payload = load_json(DEALS_PATH)

    if isinstance(payload, dict) and "items" in payload:
        return {item.get("id", item["name"]): item for item in payload.get("items", [])}

    previous_items: dict[str, dict[str, Any]] = {}
    for brand in payload.get("brands", []):
        if brand.get("name") != BRAND_NAME:
            continue
        for item in brand.get("items", []):
            previous_items[item.get("id", item["name"])] = item
    return previous_items


def dedupe_offers(offers: list[StoreOffer]) -> list[StoreOffer]:
    deduped: dict[tuple[str, float, str], StoreOffer] = {}
    for offer in offers:
        key = (offer.name, offer.price, offer.url)
        deduped[key] = offer
    return sorted(deduped.values(), key=lambda offer: (offer.price, offer.name))


def map_items(results: list[dict[str, Any]], timestamp: str, previous_items: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    now = datetime.now().astimezone()
    grouped: dict[str, dict[str, Any]] = {}

    for result in results:
        if not looks_like_zimmermann_dress(result):
            continue
        if looks_like_noise(result):
            continue

        title = str(result.get("title", "")).strip()
        if not title:
            continue

        offer = build_offer(result, timestamp)
        if offer is None:
            continue

        item_name = normalize_item_name(title)
        normalized_title = normalize_title(item_name)
        model_key = canonical_model_key(normalized_title)
        slug = product_slug(normalized_title)
        group_key = find_group_key(grouped, normalized_title, model_key, slug) or model_key or slug or slugify(item_name)
        release_year = extract_release_year(result, now)
        entry = grouped.setdefault(
            group_key,
            {
                "id": group_key,
                "name": item_name,
                "normalizedTitle": normalized_title,
                "imageUrl": result.get("thumbnail") or result.get("serpapi_thumbnail"),
                "releaseYear": release_year,
                "offers": [],
            },
        )

        if len(item_name) < len(entry["name"]):
            entry["name"] = item_name
        if release_year is not None:
            entry["releaseYear"] = max(entry["releaseYear"] or release_year, release_year)
        entry["imageUrl"] = entry["imageUrl"] or result.get("thumbnail") or result.get("serpapi_thumbnail")
        entry["offers"].append(offer)

    items: list[dict[str, Any]] = []
    for item_id, entry in grouped.items():
        offers = dedupe_offers(entry["offers"])
        if not offers:
            continue

        cheapest = offers[0]
        previous = previous_items.get(item_id, {})
        previous_history = previous.get("history", [])
        history = list(previous_history)
        today = datetime.fromisoformat(timestamp).date().isoformat()
        if not history or history[-1].get("price") != cheapest.price or history[-1].get("date") != today:
            history.append({"date": today, "price": cheapest.price})

        items.append(
            {
                "id": item_id,
                "name": entry["name"],
                "imageUrl": entry["imageUrl"],
                "releaseYear": entry["releaseYear"],
                "firstSeen": previous.get("firstSeen") or today,
                "cheapestStore": cheapest.name,
                "cheapestPrice": cheapest.price,
                "offers": [
                    {
                        "name": offer.name,
                        "price": offer.price,
                        "originalPrice": offer.original_price,
                        "url": offer.url,
                        "imageUrl": offer.image,
                        "updatedAt": offer.updated_at,
                    }
                    for offer in offers
                ],
                "history": history,
            }
        )

    return sorted(items, key=lambda item: item["cheapestPrice"])


def collect() -> dict[str, Any]:
    load_env_file(ENV_PATH)
    api_key = os.getenv("SERPAPI_API_KEY")

    previous_items = load_previous_items()
    timestamp = datetime.now().astimezone().isoformat(timespec="seconds")
    results = fetch_shopping_results(BRAND_QUERY, api_key)
    items = map_items(results, timestamp, previous_items)

    return {
        "brand": BRAND_NAME,
        "lastUpdated": timestamp,
        "items": items,
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
