from __future__ import annotations

import json
import os
import re
import sys
import urllib.parse
import urllib.request
from hashlib import sha1
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
WATCHLIST_PATH = PROJECT_ROOT / "config" / "watchlist.json"
SERPAPI_URL = "https://serpapi.com/search.json"
CACHE_TTL_HOURS = 24
REQUEST_TIMEOUT_SECONDS = 20
BRAND_NAME = "Zimmermann"
BRAND_QUERY = "Zimmermann dress"
FALLBACK_QUERY = "Zimmermann dresses"
MAX_DAILY_QUERIES = 2
DISCOVERY_RESULTS_LIMIT = 100
MIN_PRIMARY_RESULTS = 24
MIN_DISCOVERY_OFFERS = 3
MAX_IMMERSIVE_CALLS_PER_RUN = 8
YEAR_PATTERN = re.compile(r"\b(20\d{2})\b")
DRESS_PATTERN = re.compile(r"\b(dress|gown|minidress|maxidress|mididress|shirtdress)\b", re.IGNORECASE)
FILLER_PATTERN = re.compile(r"\b(by|womens|women|woman|size|new)\b", re.IGNORECASE)
LEADING_DESCRIPTOR_PATTERN = re.compile(
    r"^(cream|dahlia|peony|mint|hibiscus|ivory|pink|blue|yellow|floral|printed)\s+",
    re.IGNORECASE,
)
TRAILING_SIZE_PATTERN = re.compile(r"\b(xxs|xs|s|m|l|xl|xxl)\b$", re.IGNORECASE)
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
SOURCE_ALIASES = {
    "net a porter": "net-a-porter",
    "netaporter": "net-a-porter",
    "net-a-porter": "net-a-porter",
    "saks fifth avenue": "saks fifth avenue",
    "farfetch com": "farfetch",
    "farfetch.com": "farfetch",
}


@dataclass
class StoreOffer:
    name: str
    price: float
    original_price: float
    url: str
    image: str | None
    updated_at: str


def load_watchlist_queries() -> list[str]:
    if not WATCHLIST_PATH.exists():
        return []

    try:
        payload = load_json(WATCHLIST_PATH)
    except json.JSONDecodeError:
        return []

    queries: list[str] = []
    for brand in payload.get("brands", []):
        if str(brand.get("name", "")).strip().lower() != BRAND_NAME.lower():
            continue
        for query in brand.get("queries", []):
            normalized = str(query).strip()
            if normalized and normalized not in queries:
                queries.append(normalized)
    return queries


def watchlist_model_tokens() -> set[str]:
    tokens: set[str] = set()
    for query in load_watchlist_queries():
        normalized = normalize_title(query)
        for token in canonical_tokens(normalized):
            if token not in GENERIC_WORDS and len(token) >= 4:
                tokens.add(token)
    return tokens


def load_cached_results(query: str) -> list[dict[str, Any]] | None:
    cache_file = CACHE_DIR / f"{slugify(query)}.json"

    if not cache_file.exists():
        return None

    age = datetime.now() - datetime.fromtimestamp(cache_file.stat().st_mtime)
    if age.total_seconds() > CACHE_TTL_HOURS * 3600:
        return None

    try:
        payload = load_json(cache_file)
    except json.JSONDecodeError:
        return None

    return payload if isinstance(payload, list) else None


def fetch_immersive_offers(page_token: str, api_key: str | None) -> list[dict[str, Any]]:
    cache_file = CACHE_DIR / f"immersive-{sha1(page_token.encode('utf-8')).hexdigest()[:16]}.json"

    if cache_file.exists():
        age = datetime.now() - datetime.fromtimestamp(cache_file.stat().st_mtime)
        if age.total_seconds() <= CACHE_TTL_HOURS * 3600:
            try:
                payload = load_json(cache_file)
                if isinstance(payload, list) and payload:
                    return payload
            except json.JSONDecodeError:
                pass

    if not api_key:
        return []

    params = {"engine": "google_immersive_product", "page_token": page_token, "api_key": api_key}
    url = f"{SERPAPI_URL}?{urllib.parse.urlencode(params)}"

    try:
        with urllib.request.urlopen(url, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            payload = json.load(response)
    except Exception:
        return []

    sellers = (
        payload.get("sellers_results", {}).get("online_sellers")
        or payload.get("product_results", {}).get("stores")
        or []
    )
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    save_json(cache_file, sellers)
    return sellers


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
        "num": DISCOVERY_RESULTS_LIMIT,
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
    text_blob = get_text_blob(result)
    normalized_blob = normalize_title(text_blob)
    has_dress_signal = bool(DRESS_PATTERN.search(text_blob))

    if BRAND_NAME.lower() in text_blob.lower() and has_dress_signal:
        return True

    if not has_dress_signal:
        return False

    tracked_tokens = watchlist_model_tokens()
    if not tracked_tokens:
        return False

    blob_tokens = set(canonical_tokens(normalized_blob))
    return bool(blob_tokens & tracked_tokens)


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
    name = LEADING_DESCRIPTOR_PATTERN.sub("", name)
    name = TRAILING_SIZE_PATTERN.sub("", name).strip(" ,.-")
    name = re.sub(r"\bmini\s+dress\b", "midi dress", name, flags=re.IGNORECASE)
    name = re.sub(r"\bdrawn\s+illuminate\b", "illuminate drawn", name, flags=re.IGNORECASE)
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

    return ""


def similarity(left: str, right: str) -> float:
    return SequenceMatcher(None, left, right).ratio()


def find_group_key(grouped: dict[str, dict[str, Any]], normalized_title: str, model_key: str, slug: str) -> str | None:
    if slug in grouped:
        return slug

    for existing_slug, entry in grouped.items():
        existing_model_key = entry.get("modelKey", "")
        if model_key and existing_model_key and model_key != existing_model_key:
            continue
        if similarity(normalized_title, entry["normalizedTitle"]) >= FUZZY_MATCH_THRESHOLD:
            return existing_slug

    return None


def build_offer(result: dict[str, Any], timestamp: str) -> StoreOffer | None:
    current_price = (
        parse_price(result.get("extracted_total"))
        or parse_price(result.get("base_price"))
        or
        parse_price(result.get("extracted_price"))
        or parse_price(result.get("price"))
    )
    original_price = (
        parse_price(result.get("extracted_old_price"))
        or parse_price(result.get("old_price"))
        or parse_price(result.get("full_price"))
        or parse_price(result.get("compare_at_price"))
        or current_price
    )

    if current_price is None:
        return None

    return StoreOffer(
        name=str(result.get("seller_name") or result.get("source") or result.get("name") or "Unknown store"),
        price=current_price,
        original_price=original_price or current_price,
        url=str(result.get("product_link") or result.get("seller_link") or result.get("direct_link") or result.get("link") or ""),
        image=result.get("thumbnail") or result.get("serpapi_thumbnail") or result.get("image"),
        updated_at=timestamp,
    )


def get_page_token(result: dict[str, Any]) -> str | None:
    candidates = [
        result.get("serpapi_page_token"),
        result.get("page_token"),
        result.get("immersive_page_token"),
        result.get("immersive_product_page_token"),
    ]
    product_api = result.get("serpapi_product_api")
    if isinstance(product_api, dict):
        candidates.extend(
            [
                product_api.get("page_token"),
                product_api.get("serpapi_page_token"),
                product_api.get("immersive_page_token"),
                product_api.get("immersive_product_page_token"),
            ]
        )
    elif isinstance(product_api, str):
        parsed = urllib.parse.urlparse(product_api)
        query = urllib.parse.parse_qs(parsed.query)
        candidates.extend(query.get("page_token", []))
    immersive_api = result.get("serpapi_immersive_product_api")
    if isinstance(immersive_api, str):
        parsed = urllib.parse.urlparse(immersive_api)
        query = urllib.parse.parse_qs(parsed.query)
        candidates.extend(query.get("page_token", []))

    for candidate in candidates:
        if candidate:
            return str(candidate)

    return None


def normalize_source_name(name: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", " ", name.lower()).strip()
    return SOURCE_ALIASES.get(normalized, normalized)


def merge_price_history(
    previous_history: list[dict[str, Any]],
    today: str,
    cheapest: StoreOffer,
) -> list[dict[str, Any]]:
    history = list(previous_history)
    new_entry = {
        "date": today,
        "price": cheapest.price,
        "store": cheapest.name,
        "originalPrice": cheapest.original_price,
    }
    if not history:
        return [new_entry]

    last_entry = history[-1]
    if (
        last_entry.get("date") == today
        and last_entry.get("price") == cheapest.price
        and last_entry.get("store") == cheapest.name
        and last_entry.get("originalPrice") == cheapest.original_price
    ):
        return history

    if last_entry.get("date") == today:
        history[-1] = new_entry
        return history

    history.append(new_entry)
    return history


def merge_store_history(
    previous_store_history: list[dict[str, Any]],
    today: str,
    offers: list[StoreOffer],
) -> list[dict[str, Any]]:
    merged: dict[tuple[str, str], dict[str, Any]] = {}

    for entry in previous_store_history:
        store_name = str(entry.get("store", "")).strip()
        date = str(entry.get("date", "")).strip()
        if not store_name or not date:
            continue
        merged[(date, normalize_source_name(store_name))] = dict(entry)

    for offer in offers:
        merged[(today, normalize_source_name(offer.name))] = {
            "date": today,
            "store": offer.name,
            "price": offer.price,
            "originalPrice": offer.original_price,
            "url": offer.url,
        }

    return sorted(
        merged.values(),
        key=lambda entry: (entry.get("date", ""), str(entry.get("store", "")).lower()),
    )


def load_previous_items() -> dict[str, dict[str, Any]]:
    if not DEALS_PATH.exists():
        return {}

    try:
        payload = load_json(DEALS_PATH)
    except json.JSONDecodeError:
        return {}

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
        key = (
            normalize_source_name(offer.name),
            round(offer.price, 2),
            round(offer.original_price, 2),
        )
        previous = deduped.get(key)
        if previous is None or len(offer.url) > len(previous.url):
            deduped[key] = offer
    return sorted(deduped.values(), key=lambda offer: (offer.price, offer.name))


def merge_item_records(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []

    for item in items:
        cheapest_offer = item["offers"][0] if item.get("offers") else None
        duplicate = next(
            (
                existing
                for existing in merged
                if existing.get("imageUrl")
                and existing.get("imageUrl") == item.get("imageUrl")
                and existing.get("cheapestStore") == item.get("cheapestStore")
                and existing.get("cheapestPrice") == item.get("cheapestPrice")
                and cheapest_offer
                and existing.get("offers")
                and existing["offers"][0].get("originalPrice") == cheapest_offer.get("originalPrice")
            ),
            None,
        )

        if duplicate is None:
            merged.append(item)
            continue

        if len(item["name"]) > len(duplicate["name"]):
            duplicate["name"] = item["name"]

        duplicate["releaseYear"] = max(duplicate.get("releaseYear") or 0, item.get("releaseYear") or 0) or None
        duplicate["firstSeen"] = min(duplicate.get("firstSeen") or item["firstSeen"], item.get("firstSeen") or duplicate["firstSeen"])

        combined_offers = [
            StoreOffer(
                name=offer["name"],
                price=float(offer["price"]),
                original_price=float(offer["originalPrice"]),
                url=offer["url"],
                image=offer.get("imageUrl"),
                updated_at=offer["updatedAt"],
            )
            for offer in [*duplicate.get("offers", []), *item.get("offers", [])]
        ]
        deduped_combined = dedupe_offers(combined_offers)
        duplicate["offers"] = [
            {
                "name": offer.name,
                "price": offer.price,
                "originalPrice": offer.original_price,
                "url": offer.url,
                "imageUrl": offer.image,
                "updatedAt": offer.updated_at,
            }
            for offer in deduped_combined
        ]

        duplicate["cheapestStore"] = duplicate["offers"][0]["name"]
        duplicate["cheapestPrice"] = duplicate["offers"][0]["price"]

        history_map: dict[tuple[str, float, str], dict[str, Any]] = {}
        for entry in [*duplicate.get("history", []), *item.get("history", [])]:
            key = (
                str(entry.get("date", "")),
                float(entry.get("price", 0)),
                str(entry.get("store", "")),
            )
            history_map[key] = dict(entry)
        duplicate["history"] = sorted(history_map.values(), key=lambda entry: str(entry.get("date", "")))

        store_history_map: dict[tuple[str, str, float], dict[str, Any]] = {}
        for entry in [*duplicate.get("storeHistory", []), *item.get("storeHistory", [])]:
            key = (
                str(entry.get("date", "")),
                normalize_source_name(str(entry.get("store", ""))),
                float(entry.get("price", 0)),
            )
            store_history_map[key] = dict(entry)
        duplicate["storeHistory"] = sorted(
            store_history_map.values(),
            key=lambda entry: (str(entry.get("date", "")), str(entry.get("store", "")).lower()),
        )

    return merged


def map_items(
    results: list[dict[str, Any]],
    timestamp: str,
    previous_items: dict[str, dict[str, Any]],
    api_key: str | None,
) -> list[dict[str, Any]]:
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
        if not slug:
            continue
        group_key = find_group_key(grouped, normalized_title, model_key, slug) or slug or slugify(item_name)
        release_year = extract_release_year(result, now)
        entry = grouped.setdefault(
            group_key,
            {
                "id": group_key,
                "name": item_name,
                "normalizedTitle": normalized_title,
                "modelKey": model_key,
                "imageUrl": result.get("thumbnail") or result.get("serpapi_thumbnail"),
                "releaseYear": release_year,
                "offers": [],
                "pageTokens": set(),
            },
        )

        if len(item_name) < len(entry["name"]):
            entry["name"] = item_name
        if release_year is not None:
            entry["releaseYear"] = max(entry["releaseYear"] or release_year, release_year)
        entry["imageUrl"] = entry["imageUrl"] or result.get("thumbnail") or result.get("serpapi_thumbnail")
        entry["offers"].append(offer)
        page_token = get_page_token(result)
        if page_token:
            entry["pageTokens"].add(page_token)

    items: list[dict[str, Any]] = []
    immersive_calls = 0
    for item_id, entry in grouped.items():
        if len(entry["offers"]) < MIN_DISCOVERY_OFFERS and immersive_calls < MAX_IMMERSIVE_CALLS_PER_RUN:
            for page_token in sorted(entry["pageTokens"]):
                immersive_offers = fetch_immersive_offers(page_token, api_key)
                if not immersive_offers:
                    continue
                for immersive_offer in immersive_offers:
                    offer = build_offer(immersive_offer, timestamp)
                    if offer is not None:
                        entry["offers"].append(offer)
                immersive_calls += 1
                break
        offers = dedupe_offers(entry["offers"])
        if not offers:
            continue

        cheapest = offers[0]
        previous = previous_items.get(item_id, {})
        previous_history = previous.get("history", [])
        previous_store_history = previous.get("storeHistory", [])
        today = datetime.fromisoformat(timestamp).date().isoformat()
        history = merge_price_history(previous_history, today, cheapest)
        store_history = merge_store_history(previous_store_history, today, offers)

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
                "storeHistory": store_history,
            }
        )

    return sorted(merge_item_records(items), key=lambda item: item["cheapestPrice"])


def gather_discovery_results(api_key: str | None) -> list[dict[str, Any]]:
    queries = load_watchlist_queries() or [BRAND_QUERY]
    primary_query = queries[0]
    results = fetch_shopping_results(primary_query, api_key)

    if len(results) < MIN_PRIMARY_RESULTS and MAX_DAILY_QUERIES > 1:
        for fallback_query in [BRAND_QUERY, FALLBACK_QUERY]:
            if fallback_query not in queries:
                queries.append(fallback_query)
            if len(queries) >= MAX_DAILY_QUERIES:
                break

    merged: dict[str, dict[str, Any]] = {}
    for query in queries:
        for result in fetch_shopping_results(query, api_key):
            key = str(result.get("product_id") or result.get("title") or result.get("link") or "")
            if key and key not in merged:
                merged[key] = result

    return list(merged.values())


def collect() -> dict[str, Any]:
    load_env_file(ENV_PATH)
    api_key = os.getenv("SERPAPI_API_KEY")

    previous_items = load_previous_items()
    timestamp = datetime.now().astimezone().isoformat(timespec="seconds")
    results = gather_discovery_results(api_key)
    items = map_items(results, timestamp, previous_items, api_key)

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
