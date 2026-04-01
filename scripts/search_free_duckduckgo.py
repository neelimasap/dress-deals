#!/usr/bin/env python3
"""
Free DuckDuckGo Instant Answer API for basic product search.
No API key required - completely free!
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from typing import Any

def search_duckduckgo(query: str) -> dict[str, Any] | None:
    """Search using DuckDuckGo Instant Answer API (completely free)"""
    params = {
        'q': query,
        'format': 'json',
        'no_html': '1',
        'skip_disambig': '1'
    }

    url = f"https://api.duckduckgo.com/?{urllib.parse.urlencode(params)}"

    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            return json.loads(response.read().decode('utf-8'))
    except Exception as e:
        print(f"DuckDuckGo search failed: {e}")
        return None

def extract_product_info(ddg_results: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract product/shopping info from DuckDuckGo response"""
    items = []

    # DuckDuckGo Instant Answers are limited but can include product info
    if ddg_results.get('Answer'):
        items.append({
            'title': ddg_results.get('Answer', ''),
            'source': 'DuckDuckGo Instant Answer',
            'type': 'instant_answer'
        })

    # Check for related topics/products
    if 'RelatedTopics' in ddg_results:
        for topic in ddg_results['RelatedTopics'][:3]:  # Limit results
            if isinstance(topic, dict) and 'Text' in topic:
                items.append({
                    'title': topic['Text'],
                    'url': topic.get('FirstURL', ''),
                    'source': 'DuckDuckGo Related',
                    'type': 'related_topic'
                })

    return items

def main():
    """Demo: Search for Zimmermann dresses using free DuckDuckGo API"""
    queries = [
        "Zimmermann dress sale",
        "Zimmermann new collection",
        "Marchesa gown discount"
    ]

    for query in queries:
        print(f"\n🔍 DuckDuckGo Search: {query}")

        results = search_duckduckgo(query)
        if results:
            items = extract_product_info(results)
            print(f"✅ Found {len(items)} results:")

            for item in items:
                print(f"• {item['title'][:100]}...")
                if item.get('url'):
                    print(f"  URL: {item['url']}")
                print(f"  Source: {item['source']}\n")
        else:
            print("❌ No results")

        # Rate limiting - free APIs need breaks
        import time
        time.sleep(1)

if __name__ == "__main__":
    main()