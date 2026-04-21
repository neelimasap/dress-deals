# Dress Deal Tracker

Tracks the cheapest recent Zimmermann dress offers from one cached Google Shopping query.

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
```

The GitHub token must be allowed to dispatch Actions workflows for the target repository.

## Free Hosting

You can host the frontend for free with:

- Vercel
- Netlify

That gives you a shareable link such as `dress-deals.vercel.app`.

## Cost Control

Use `data/cache/` and refresh prices once per day to avoid wasting SerpApi credits.
