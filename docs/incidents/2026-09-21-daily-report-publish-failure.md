# Incident: Daily report could not be published

- **Date detected:** 2026-09-21
- **Severity:** SEV-3 — automation degraded; cached deal data remained available
- **Status:** Resolved in the production-hardening change set
- **Affected component:** Scheduled GitHub Actions refresh

## Summary

The daily refresh workflow generated `reports/daily-deals.md` and then attempted to add it to the
refresh commit. The entire `reports/` directory was excluded by `.gitignore`, so a clean runner
could not stage the generated report. The website linked directly to that file, which meant the
report could be missing even when the frontend itself loaded.

## Customer impact

- The **Open daily report** link could return a missing file.
- The scheduled workflow could stop at the commit step instead of publishing newly collected data.
- There was no automatic issue or other durable notification explaining that the refresh failed.

The cached `data/deals.json` file remained readable, so the primary browsing experience continued
to show the last successfully published snapshot.

## Detection

The failure was reproduced during the repository production-readiness review with:

```text
git check-ignore -v reports/daily-deals.md
```

The command confirmed that `.gitignore` excluded the same file the workflow attempted to publish.

## Root cause

The generated report was treated as a disposable local build artifact in `.gitignore`, while the
runtime UI and deployment workflow treated it as a versioned production artifact. Those two
contracts were inconsistent. The workflow also lacked a test that generated and staged the report
on a clean checkout.

## Resolution

1. Keep temporary report output ignored while explicitly allowing `reports/daily-deals.md`.
2. Generate and validate the report in CI on every pull request and push.
3. Commit the report together with `data/deals.json` and `data/run-metrics.json` after a refresh.
4. Open or update a GitHub issue automatically when the scheduled refresh fails.
5. Close the failure issue after the next successful run.

## Prevention and follow-up

- The `npm run build` contract now validates deal data and generates the report.
- CI runs lint, unit tests, the build contract, and a Docker image build.
- Scheduled runs emit structured JSON logs and persist bounded run-history metrics.
- Publishing paths must be checked from a clean clone before deployment changes are merged.
