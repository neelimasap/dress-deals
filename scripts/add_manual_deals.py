#!/usr/bin/env python3
"""
Manual deal entry - Add dress deals without API calls.
Perfect for exclusive sales you find manually.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEALS_PATH = PROJECT_ROOT / "data" / "deals.json"

def load_deals() -> dict[str, Any]:
    """Load current deals data"""
    if not DEALS_PATH.exists():
        return {"lastUpdated": datetime.now().isoformat(), "brands": []}

    with open(DEALS_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_deals(data: dict[str, Any]) -> None:
    """Save deals data"""
    data["lastUpdated"] = datetime.now().isoformat()
    with open(DEALS_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def add_manual_deal():
    """Interactive manual deal entry"""
    print("🛍️  Manual Deal Entry (No API calls needed!)")
    print("=" * 50)

    # Get brand
    brands = ["Zimmermann", "Marchesa"]
    print("\nAvailable brands:")
    for i, brand in enumerate(brands, 1):
        print(f"{i}. {brand}")

    while True:
        try:
            brand_choice = int(input("\nSelect brand (1-2): ")) - 1
            if 0 <= brand_choice < len(brands):
                brand_name = brands[brand_choice]
                break
            print("Invalid choice. Try again.")
        except ValueError:
            print("Please enter a number.")

    # Get deal details
    print(f"\nAdding deal for {brand_name}:")
    dress_name = input("Dress name: ").strip()
    if not dress_name:
        print("❌ Dress name required")
        return

    store_name = input("Store name (e.g., Saks Fifth Avenue): ").strip()
    if not store_name:
        print("❌ Store name required")
        return

    try:
        price = float(input("Current price: $").strip())
        original_price = float(input("Original price: $").strip())
    except ValueError:
        print("❌ Invalid price format")
        return

    image_url = input("Image URL (optional): ").strip() or None
    product_url = input("Product URL: ").strip()
    if not product_url:
        print("❌ Product URL required")
        return

    # Load existing data
    data = load_deals()

    # Find or create brand
    brand_data = None
    for brand in data["brands"]:
        if brand["name"] == brand_name:
            brand_data = brand
            break

    if not brand_data:
        brand_data = {"name": brand_name, "items": []}
        data["brands"].append(brand_data)

    # Create new deal item
    timestamp = datetime.now().isoformat()
    deal_id = f"manual-{int(datetime.now().timestamp())}"

    new_item = {
        "id": deal_id,
        "name": f"{brand_name} {dress_name}",
        "imageUrl": image_url,
        "releaseYear": None,
        "firstSeen": datetime.now().strftime("%Y-%m-%d"),
        "cheapestStore": store_name,
        "cheapestPrice": price,
        "offers": [{
            "name": store_name,
            "price": price,
            "originalPrice": original_price,
            "url": product_url,
            "imageUrl": image_url,
            "updatedAt": timestamp,
            "sourceCategory": "retail"  # Assume manual entries are from retailers
        }],
        "history": [{
            "date": datetime.now().strftime("%Y-%m-%d"),
            "price": price,
            "store": store_name,
            "originalPrice": original_price
        }],
        "storeHistory": [{
            "date": datetime.now().strftime("%Y-%m-%d"),
            "store": store_name,
            "price": price,
            "originalPrice": original_price,
            "url": product_url,
            "sourceCategory": "retail"
        }]
    }

    # Add to brand items
    brand_data["items"].append(new_item)

    # Save
    save_deals(data)

    print("
✅ Deal added successfully!"    print(f"• {dress_name}")
    print(f"• {store_name}: ${price} (was ${original_price})")
    print(f"• {len(brand_data['items'])} total {brand_name} deals now")

def list_deals():
    """List current deals"""
    data = load_deals()

    print("\n📊 Current Deals Summary:")
    print("=" * 30)

    for brand in data["brands"]:
        print(f"\n{brand['name']}: {len(brand['items'])} deals")
        for item in brand["items"][-3:]:  # Show last 3
            store = item["offers"][0] if item["offers"] else {"name": "Unknown", "price": 0}
            print(f"• {item['name'][:50]}... - {store['name']}: ${store['price']}")

def main():
    """Main menu"""
    while True:
        print("\n" + "="*50)
        print("🛍️  MANUAL DEAL ENTRY (FREE - No API calls!)")
        print("="*50)
        print("1. Add new deal")
        print("2. List current deals")
        print("3. Exit")

        choice = input("\nChoose option (1-3): ").strip()

        if choice == "1":
            add_manual_deal()
        elif choice == "2":
            list_deals()
        elif choice == "3":
            print("👋 Goodbye!")
            break
        else:
            print("❌ Invalid choice")

if __name__ == "__main__":
    main()