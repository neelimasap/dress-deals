# Architecture

## System Flow

`fetch_serpapi.py`
-> SerpApi
-> `deals.json`
-> frontend UI

## Notes

- `scripts/fetch_serpapi.py` performs one Zimmermann Google Shopping query per 24 hours.
- `scripts/fetch_serpapi.py` filters for dress items that expose a recent release year marker.
- `data/deals.json` stores current prices and history.
- `data/cache/` reduces repeat API calls.
- The frontend reads `data/deals.json` directly.
