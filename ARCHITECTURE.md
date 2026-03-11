# Architecture

## System Flow

`watchlist.json`
-> `collect_deals.py`
-> SerpApi
-> `deals.json`
-> frontend UI

## Notes

- `config/watchlist.json` defines tracked brands and queries.
- `scripts/fetch_serpapi.py` collects and normalizes shopping results.
- `data/deals.json` stores current prices and history.
- `data/cache/` reduces repeat API calls.
- The frontend reads `data/deals.json` directly.
