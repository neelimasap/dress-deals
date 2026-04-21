# Architecture

## System Flow

`watchlist.json`
-> `collect_deals.py`
-> `fetch_serpapi.py`
-> SerpApi
-> `deals.json`
-> frontend UI

## Notes

- `config/watchlist.json` defines tracked brands and queries.
- `scripts/fetch_serpapi.py` performs one Zimmermann Google Shopping query per 24 hours.
- `scripts/fetch_serpapi.py` collects, normalizes, and filters shopping results.
- `scripts/fetch_serpapi.py` filters for dress items that expose a recent release year marker.
- `data/deals.json` stores current prices and history.
- `data/cache/` reduces repeat API calls.
- The frontend reads `data/deals.json` directly.
