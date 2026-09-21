# Setup

## Native development

1. Install Python 3.12 and Node.js 20.
2. Copy `.env.example` to `.env` and configure the required secrets.
3. Install the development tools:

```bash
python -m pip install -r requirements-dev.txt
```

4. Run the collector:

```bash
python scripts/collect_deals.py
```

5. Run all quality gates:

```bash
npm run check
```

6. Start the local preview:

```bash
npm run serve
```

## Docker development

Build and run the web application:

```bash
docker compose up --build web
```

Run a collection inside the container:

```bash
docker compose --profile tools run --rm collector
```

Both services bind-mount `data/` and `reports/` so generated artifacts remain available locally.

## Production environment

Configure these values in the deployment platform:

- `GITHUB_TOKEN`: fine-grained token allowed to dispatch Actions for this repository
- `GITHUB_REPOSITORY`: `neelimasap/dress-deals`
- `GITHUB_REFRESH_WORKFLOW`: `daily-refresh.yml`
- `GITHUB_REFRESH_REF`: `main`
- `REFRESH_SECRET`: long random secret known only to the administrator

Configure `SERPAPI_API_KEY` as a GitHub Actions repository secret, not as a public frontend value.
