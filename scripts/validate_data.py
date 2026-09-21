from __future__ import annotations

import argparse
import math
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from observability import log_event
from utils import load_json

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATA_PATH = PROJECT_ROOT / "data" / "deals.json"
ALLOWED_SOURCE_CATEGORIES = {"retail", "aggregator", "resale"}
DEFAULT_MAX_DROP_FRACTION = 0.5


def _positive_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value > 0


def _valid_http_url(value: Any) -> bool:
    if not isinstance(value, str) or not value:
        return False
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def validate_payload(payload: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(payload, dict):
        return ["payload must be a JSON object"]

    try:
        datetime.fromisoformat(str(payload.get("lastUpdated", "")))
    except ValueError:
        errors.append("lastUpdated must be an ISO-8601 timestamp")

    brands = payload.get("brands")
    if not isinstance(brands, list) or not brands:
        errors.append("brands must be a non-empty list")
        return errors

    brand_names: set[str] = set()
    for brand_index, brand in enumerate(brands):
        prefix = f"brands[{brand_index}]"
        if not isinstance(brand, dict):
            errors.append(f"{prefix} must be an object")
            continue

        name = str(brand.get("name", "")).strip()
        if not name:
            errors.append(f"{prefix}.name is required")
        elif name.casefold() in brand_names:
            errors.append(f"{prefix}.name duplicates another brand: {name}")
        brand_names.add(name.casefold())

        items = brand.get("items")
        if not isinstance(items, list):
            errors.append(f"{prefix}.items must be a list")
            continue

        item_ids: set[str] = set()
        for item_index, item in enumerate(items):
            item_prefix = f"{prefix}.items[{item_index}]"
            if not isinstance(item, dict):
                errors.append(f"{item_prefix} must be an object")
                continue

            item_id = str(item.get("id", "")).strip()
            if not item_id:
                errors.append(f"{item_prefix}.id is required")
            elif item_id in item_ids:
                errors.append(f"{item_prefix}.id is duplicated: {item_id}")
            item_ids.add(item_id)

            if not str(item.get("name", "")).strip():
                errors.append(f"{item_prefix}.name is required")

            offers = item.get("offers")
            if not isinstance(offers, list) or not offers:
                errors.append(f"{item_prefix}.offers must be a non-empty list")
                continue

            valid_prices: list[float] = []
            for offer_index, offer in enumerate(offers):
                offer_prefix = f"{item_prefix}.offers[{offer_index}]"
                if not isinstance(offer, dict):
                    errors.append(f"{offer_prefix} must be an object")
                    continue
                price = offer.get("price")
                original_price = offer.get("originalPrice")
                if not _positive_number(price):
                    errors.append(f"{offer_prefix}.price must be a positive finite number")
                else:
                    valid_prices.append(float(price))
                if not _positive_number(original_price):
                    errors.append(f"{offer_prefix}.originalPrice must be a positive finite number")
                elif _positive_number(price) and float(original_price) < float(price):
                    errors.append(f"{offer_prefix}.originalPrice cannot be below price")
                if not str(offer.get("name", "")).strip():
                    errors.append(f"{offer_prefix}.name is required")
                if not _valid_http_url(offer.get("url")):
                    errors.append(f"{offer_prefix}.url must be an absolute HTTP(S) URL")
                if offer.get("sourceCategory") not in ALLOWED_SOURCE_CATEGORIES:
                    errors.append(
                        f"{offer_prefix}.sourceCategory must be one of {sorted(ALLOWED_SOURCE_CATEGORIES)}"
                    )

            if valid_prices:
                minimum = min(valid_prices)
                if not _positive_number(item.get("cheapestPrice")) or not math.isclose(
                    float(item["cheapestPrice"]), minimum, abs_tol=0.01
                ):
                    errors.append(f"{item_prefix}.cheapestPrice must equal the lowest offer price ({minimum})")

    return errors


def validate_against_previous(
    current: dict[str, Any],
    previous: dict[str, Any],
    max_drop_fraction: float = DEFAULT_MAX_DROP_FRACTION,
) -> list[str]:
    """Reject implausible item-count collapses caused by upstream/API failures."""
    if not previous or not isinstance(previous.get("brands"), list):
        return []

    previous_counts = {
        str(brand.get("name", "")): len(brand.get("items", []))
        for brand in previous["brands"]
        if isinstance(brand, dict) and isinstance(brand.get("items"), list)
    }
    current_counts = {
        str(brand.get("name", "")): len(brand.get("items", []))
        for brand in current.get("brands", [])
        if isinstance(brand, dict) and isinstance(brand.get("items"), list)
    }

    errors: list[str] = []
    for brand_name, previous_count in previous_counts.items():
        if previous_count == 0:
            continue
        current_count = current_counts.get(brand_name, 0)
        minimum_allowed = math.floor(previous_count * (1 - max_drop_fraction))
        if current_count < minimum_allowed:
            errors.append(
                f"{brand_name} item count dropped from {previous_count} to {current_count}; "
                f"minimum allowed is {minimum_allowed}"
            )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate generated deal data before publishing it.")
    parser.add_argument("path", nargs="?", type=Path, default=DEFAULT_DATA_PATH)
    args = parser.parse_args()

    try:
        payload = load_json(args.path)
    except (OSError, ValueError) as error:
        log_event("error", "data_validation_failed", path=str(args.path), error=str(error))
        return 1

    errors = validate_payload(payload)
    if errors:
        for error in errors:
            log_event("error", "data_validation_error", path=str(args.path), detail=error)
        log_event("error", "data_validation_failed", path=str(args.path), error_count=len(errors))
        return 1

    item_count = sum(len(brand.get("items", [])) for brand in payload.get("brands", []))
    log_event(
        "info",
        "data_validation_passed",
        path=str(args.path),
        brand_count=len(payload["brands"]),
        item_count=item_count,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
