# API Usage

## Discovery queries

Queries are generated from each brand's primary queries, fallback queries, discovery terms, and
sale modifiers in `config/watchlist.json`. A run is capped at 24 queries per brand.

## Estimated Usage

Actual call count depends on cache state and the number of configured brands. Each run records
`queries_attempted`, `api_requests`, `api_errors`, `cache_hits`, and `cache_misses` in
`data/run-metrics.json`.

The collector caches raw Google Shopping responses in `data/cache/` for seven days. Repeated runs
reuse valid cached responses instead of consuming another SerpApi request.

## Refresh endpoint

`POST /api/refresh` queues the `daily-refresh.yml` workflow. It requires:

```http
Authorization: Bearer <REFRESH_SECRET>
```

Responses:

- `202`: workflow accepted by GitHub
- `401`: missing or invalid refresh secret
- `503`: refresh authentication or the GitHub token is not configured
- `502`: GitHub rejected the dispatch or could not be reached

Upstream response bodies are intentionally excluded from client responses.
