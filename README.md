# Dress Deal Tracker

<<<<<<< HEAD
Tracks the cheapest recent Zimmermann dress offers from one cached Google Shopping query.
=======
Tracks the best prices for selected dress brands.
>>>>>>> 7cac992bb87289d5a5c4636070be74c4a79b99d3

## Data Source

SerpApi Google Shopping results.

## Features

<<<<<<< HEAD
- One daily brand-level query
- 24 hour local response caching
- Recent-release filtering
- Cheapest-offer aggregation
=======
- Price comparison
- Dress images
- Price history
>>>>>>> 7cac992bb87289d5a5c4636070be74c4a79b99d3
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

<<<<<<< HEAD
Use `data/cache/` and refresh prices once per day to avoid wasting SerpApi credits.
=======
Use `data/cache/` and refresh prices once per day to avoid wasting SerpApi credits and AI tokens.
>>>>>>> 7cac992bb87289d5a5c4636070be74c4a79b99d3
