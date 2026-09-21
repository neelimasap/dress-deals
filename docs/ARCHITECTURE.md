# Architecture

## System flow

```text
config/watchlist.json
        |
        v
scheduled/manual GitHub Action ---> SerpApi
        |                               |
        v                               v
scripts/collect_deals.py <--- seven-day raw-response cache
        |
        +--> normalize, match, filter, deduplicate
        +--> schema and regression quality gates
        +--> structured JSON logs + run metrics
        |
        v
data/deals.json + reports/daily-deals.md
        |
        v
static frontend / Vercel
```

## Component responsibilities

- `config/watchlist.json` is the declarative source of tracked brands, queries, price rules, and
  trusted or blocked sellers.
- `scripts/fetch_serpapi.py` owns acquisition, cache behavior, normalization, entity matching,
  offer deduplication, price history, and fail-closed publishing.
- `scripts/validate_data.py` verifies the published contract and detects catastrophic item-count
  regressions against the last good snapshot.
- `scripts/observability.py` emits structured logs and stores a bounded 30-run metrics history.
- `data/deals.json` is the immutable frontend input for one deployment.
- `api/refresh.js` authenticates an administrative refresh request before dispatching GitHub
  Actions. The GitHub credential remains server-side.
- `frontend/app.js` renders the cached production snapshot and performs no direct retailer calls.

## Reliability boundaries

- API calls have a 20-second timeout.
- Raw shopping responses are cached for seven days to control cost and tolerate transient outages.
- A brand-level item-count drop greater than 50% stops publication unless an operator explicitly
  sets `ALLOW_LARGE_DATA_DROP=1` for an intentional reset.
- GitHub Actions concurrency prevents overlapping scheduled refreshes.
- Failed runs create a durable GitHub issue containing the workflow-run link.

## Security boundaries

- `SERPAPI_API_KEY`, `GITHUB_TOKEN`, and `REFRESH_SECRET` are environment secrets.
- `/api/refresh` requires a timing-safe bearer-token check.
- Upstream error bodies are written only to server logs and are not returned to public clients.
- The browser never receives the GitHub token.
