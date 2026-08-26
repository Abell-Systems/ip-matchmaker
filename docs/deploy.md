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
  --set-env-vars "GEMINI_API_KEY=<PASTE_KEY>,GEMINI_MODEL=gemini-3.5-flash,USE_MOCK_BIGQUERY=false"
```

Notes:
- `--source .` uses the multi-stage `Dockerfile` at root to compile React (`npm run build`) and bundle it directly into FastAPI.
- Serves both SPA UI and REST endpoints on a single HTTPS URL.
- Zero external dependencies (no Vercel, Netlify, or third-party proxy).
- Grab the URL: `gcloud run services describe patent-agent --region us-central1 --format 'value(status.url)'`

Smoke test:
- Open `<cloud-run-url>` in browser to see User Zero UI.
- Curl API: `curl "<cloud-run-url>/health"`

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
