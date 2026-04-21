# Setup

1. Install Python.
2. Add `SERPAPI_API_KEY` to `.env`.
3. Run:

```bash
python scripts/collect_deals.py
```

4. Generate the markdown report:

```bash
node scripts/generate-report.mjs
```

5. Start the local preview:

```bash
node scripts/serve.mjs
```
