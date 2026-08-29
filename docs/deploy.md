# Single Container Cloud Run Deployment (100% Google Cloud)

Target: User Zero validation and judge demonstration via a single unified Google Cloud Run URL (`https://patent-agent-....run.app`). The Cloud Run URL doubles as the required "visible Google Cloud" evidence for the demo video.

## 0. Prerequisites (one-time, needs the GCP account owner)

1. Log into Google Cloud Console → create project `ip-matchmaker`.
2. Install `gcloud` CLI:
   ```bash
   gcloud auth login
   gcloud config set project ip-matchmaker
   ```

## 1. Single Command Cloud Run Deploy

```bash
gcloud services enable run.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com

gcloud run deploy patent-agent \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars "GEMINI_API_KEY=<PASTE_KEY>,GEMINI_MODEL=gemini-3.5-flash,USE_MOCK_BIGQUERY=true"
```

`USE_MOCK_BIGQUERY=true` here is deliberate, not a placeholder — see §2 below before changing it.

Notes:
- `--source .` uses the multi-stage `Dockerfile` at root to compile React (`npm run build`) and bundle it directly into FastAPI.
- Serves both SPA UI and REST endpoints on a single HTTPS URL.
- Zero external dependencies (no Vercel, Netlify, or third-party proxy).
- Grab the URL: `gcloud run services describe patent-agent --region us-central1 --format 'value(status.url)'`

Smoke test:
- Open `<cloud-run-url>` in browser to see User Zero UI.
- Curl API: `curl "<cloud-run-url>/health"`

## 2. BigQuery rollout status

`USE_MOCK_BIGQUERY=false` is a deliberately staged rollout, not a single flag flip, because
the risk here isn't BigQuery failing (the code already falls back to mock on any error) --
it's BigQuery working too well and running up cost against a public, unauthenticated
endpoint, or reporting as "real" data on a method that's still mocked underneath. The agreed
sequence is:

| Step | Status |
|---|---|
| Cost cap (`maximum_bytes_billed`, env-tunable) + in-process TTL cache on every real query | ✅ Done |
| `get_patents_datasource()` memoized so the cache/client survive across requests | ✅ Done |
| Observability: `/health` reports actual `patents_datasource` status (bigquery / bigquery_cached / mock_fallback), not just the config flag; `get_status()` lists which methods are genuinely real | ✅ Done |
| `get_citations` wired to a real query (self-joins `patents-public-data.patents.publications`'s own `citation` field) | ✅ Done |
| `get_similar_patents` real query (needs `google_patents_research.publications`'s precomputed similarity fields — separate table, separate cost profile) | Not started, not blocking |
| IAM: grant the **Cloud Run runtime service account** (not the deploy-time workload-identity principal in `deploy.yml` -- confirm the actual runtime SA identity for this project first, don't assume it's the default compute SA) `roles/bigquery.jobUser` | ⛔ Not started |
| Real-credentials integration test (currently `test_bigquery_real.py` only exercises the mocked-client fallback path) | ⛔ Not started |
| Dry-run against the live public dataset to measure actual bytes scanned and sanity-check the `BIGQUERY_MAX_BYTES_BILLED` default | ⛔ Not started |
| Flip `USE_MOCK_BIGQUERY=false` in `.github/workflows/deploy.yml` | ⛔ **Blocked pending review** -- do not flip until IAM → integration test → dry-run have each landed and been checked, in that order |

## 3. Quota & Cost Reality Check

> **Estimated demo infrastructure cost: $0.**
> The prototype is designed to run within the applicable Google Cloud and Gemini free-tier quotas. Cloud Run provides a monthly free tier for low-volume workloads, and the demo's expected usage is substantially below those limits. Gemini usage is likewise intended to remain within the applicable free-tier quota. No paid infrastructure is required for the expected hackathon demonstration workload.
>
> A Google Cloud project and billing-enabled account may be required to deploy Cloud Run. Actual charges depend on current Google Cloud pricing, quotas, region, and account configuration.

Free tier quota: **5 req/min and 20 req/day per model.** One full graph run ≈ 20 calls,
so each User Zero gets roughly one pipeline run per day. Mitigations:

- Set `GEMINI_MODEL=gemini-3.5-flash-lite` in Cloud Run env vars for validation runs
  (separate per-model quota bucket); keep flash for the recorded demo.
- Or attach billing to the project — trial credit absorbs it and paid tier removes
  the daily cap.

## 4. Post-deploy checklist

- [ ] `/health` returns ok over HTTPS
- [ ] `/api/landscape` returns clusters from the frontend origin (CORS passes)
- [ ] Full agent run works via `adk web` locally against the same key before demoing
- [ ] Cloud Run dashboard visible on screen during demo recording (requirement §1)
