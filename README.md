# Dress Deal Tracker

Tracks the cheapest recent Zimmermann dress offers from one cached Google Shopping query.

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

## Free Hosting

You can host the frontend for free with:

- Vercel
- Netlify

That gives you a shareable link such as `dress-deals.vercel.app`.

## Cost Control

Use `data/cache/` and refresh prices once per day to avoid wasting SerpApi credits.
