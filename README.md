# Dress Deal Intelligence

Tracks and compares discounted designer clothing across trusted retailers. The project is also a
production-engineering case study: scheduled data ingestion, normalization, fuzzy entity matching,
quality gates, authenticated operations, structured telemetry, CI, and containerized execution.

## Project Layout

- App entry files stay at the repo root: `index.html`, `service-worker.js`, `manifest.webmanifest`
- Browser code lives in `frontend/`
- Serverless and local API handlers live in `api/`
- Data and generated reports live in `data/` and `reports/`
- Collector and utility scripts live in `scripts/`
- Configuration lives in `config/`
- Project notes and reference docs live in `docs/`

## Data Source

SerpApi Google Shopping results.

## Features

- One daily brand-level query
- 24 hour local response caching
- Recent-release filtering
- Cheapest-offer aggregation
- Markdown daily reports
- Fail-closed data-quality validation
- Structured JSON logs and bounded run metrics
- Authenticated workflow refresh
- Automated failure issues

## Run Locally

```bash
python scripts/fetch_serpapi.py
node scripts/generate-report.mjs
node scripts/serve.mjs
```

Open `http://localhost:4173`.

## Refresh Button

The site refresh button queues the GitHub Actions `daily-refresh.yml` workflow instead of updating data in-place.

Set these environment variables in Vercel and local preview if you want the button to work:

```bash
GITHUB_TOKEN=...
GITHUB_REPOSITORY=neelimasap/dress-deals
GITHUB_REFRESH_WORKFLOW=daily-refresh.yml
GITHUB_REFRESH_REF=main
REFRESH_SECRET=generate-a-long-random-admin-secret
```

The GitHub token must be allowed to dispatch Actions workflows for the target repository. The UI
asks for `REFRESH_SECRET` when an administrator queues a refresh; the value is sent as a bearer
token and is never committed or stored by the app.

## Quality Gates

Run the same contract used by CI:

```bash
python -m pip install -r requirements-dev.txt
npm run check
```

The checks cover Python and JavaScript linting, normalization and fuzzy matching, offer
deduplication, bad upstream responses, refresh authentication, data-schema validation, and report
generation.

Generated data is compared with the last good snapshot. A drop greater than 50% for any tracked
brand fails the collection instead of publishing a likely-empty result after an upstream outage.
For an intentional catalog reset, an operator may run once with `ALLOW_LARGE_DATA_DROP=1`.

## Docker

```bash
docker compose up --build web
```

Open `http://localhost:4173`. To run the collector inside the same reproducible image:

```bash
docker compose --profile tools run --rm collector
```

## Operations

- Collection events are emitted as one JSON object per log line.
- The latest run and the last 30 runs are stored in `data/run-metrics.json`.
- Failed scheduled refreshes open or update a GitHub issue; a later successful run closes it.
- Operational history and recovery notes live under `docs/incidents/`.

## Free Hosting

You can host the frontend for free with:

- Vercel
- Netlify

That gives you a shareable link such as `dress-deals.vercel.app`.

## Cost Control

Use `data/cache/` and refresh prices once per day to avoid wasting SerpApi credits.
