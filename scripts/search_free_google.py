#!/usr/bin/env python3
"""
Free Google Custom Search API alternative for dress deals.
Get your API key at: https://console.developers.google.com/
Create a Custom Search Engine at: https://cse.google.com/
"""

from __future__ import annotations

import json
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from utils import load_env_file, load_json, save_json

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = PROJECT_ROOT / ".env"

def search_google_cse(query: str, api_key: str, cse_id: str) -> dict[str, Any] | None:
    """Search using Google Custom Search API (free tier: 100 queries/day)"""
    params = {
        'key': api_key,
        'cx': cse_id,
        'q': query,
        'num': 10,  # Max 10 results per query
        'start': 1
    }

    url = f"https://www.googleapis.com/customsearch/v1?{urllib.parse.urlencode(params)}"

    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            return json.loads(response.read().decode('utf-8'))
    except Exception as e:
        print(f"Google CSE search failed: {e}")
        return None

def extract_shopping_results(cse_results: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract shopping/product results from Google CSE response"""
    items = []

    if 'items' not in cse_results:
        return items

    for item in cse_results['items']:
        # Look for shopping/product results
        if 'pagemap' in item and 'product' in item['pagemap']:
            product = item['pagemap']['product'][0]

            # Extract price information
            price = None
            if 'price' in product:
                price_str = product['price'].replace('$', '').replace(',', '')
                try:
                    price = float(price_str)
                except ValueError:
                    pass

            items.append({
                'title': item.get('title', ''),
                'link': item.get('link', ''),
                'price': price,
                'source': item.get('displayLink', ''),
                'snippet': item.get('snippet', '')
            })

    return items

def main():
    """Demo: Search for Zimmermann dresses using free Google CSE API"""
    load_env_file(ENV_PATH)

    # You'll need to set these in your .env file
    api_key = os.getenv('GOOGLE_CSE_API_KEY')
    cse_id = os.getenv('GOOGLE_CSE_ID')  # Create at cse.google.com

    if not api_key or not cse_id:
        print("❌ Missing GOOGLE_CSE_API_KEY or GOOGLE_CSE_ID in .env")
        print("\nTo get free Google CSE API:")
        print("1. Go to: https://console.developers.google.com/")
        print("2. Create project & enable 'Custom Search JSON API'")
        print("3. Get API key from Credentials")
        print("4. Create Custom Search Engine at: https://cse.google.com/")
        print("5. Get Search Engine ID")
        print("\nAdd to .env:")
        print("GOOGLE_CSE_API_KEY=your_api_key_here")
        print("GOOGLE_CSE_ID=your_cse_id_here")
        return

    query = "Zimmermann dress site:saksfifthavenue.com OR site:net-a-porter.com"
    print(f"🔍 Searching: {query}")

    results = search_google_cse(query, api_key, cse_id)
    if results:
        items = extract_shopping_results(results)
        print(f"✅ Found {len(items)} potential dress deals:")

        for item in items[:5]:  # Show first 5
            print(f"• {item['title']}")
            if item['price']:
                print(f"  Price: ${item['price']}")
            print(f"  Source: {item['source']}")
            print(f"  Link: {item['link']}\n")
    else:
        print("❌ No results found")

if __name__ == "__main__":
    main()