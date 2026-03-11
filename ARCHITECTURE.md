# Architecture

## System Flow

<<<<<<< HEAD
`fetch_serpapi.py`
=======
`watchlist.json`
-> `collect_deals.py`
>>>>>>> 7cac992bb87289d5a5c4636070be74c4a79b99d3
-> SerpApi
-> `deals.json`
-> frontend UI

## Notes

<<<<<<< HEAD
- `scripts/fetch_serpapi.py` performs one Zimmermann Google Shopping query per 24 hours.
- `scripts/fetch_serpapi.py` filters for dress items that expose a recent release year marker.
=======
- `config/watchlist.json` defines tracked brands and queries.
- `scripts/fetch_serpapi.py` collects and normalizes shopping results.
>>>>>>> 7cac992bb87289d5a5c4636070be74c4a79b99d3
- `data/deals.json` stores current prices and history.
- `data/cache/` reduces repeat API calls.
- The frontend reads `data/deals.json` directly.
