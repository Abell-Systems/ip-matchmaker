# Deploy guide — Cloud Run + static frontend

Target: User Zero validation on free resources. The Cloud Run URL also doubles as
the required "visible Google Cloud" evidence for the demo video.

## 0. Prerequisites (one-time, needs the GCP account owner)

1. Log into the **fresh** Google account (untouched $300 trial).
2. [console.cloud.google.com](https://console.cloud.google.com) → create project
   `ip-matchmaker` → accept free-trial terms when prompted for billing.
3. Install gcloud CLI, then:
   ```bash
   gcloud auth login
   gcloud config set project ip-matchmaker
   ```

## 1. Backend → Cloud Run

```bash
gcloud services enable run.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com

cd backend
gcloud run deploy patent-agent \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars "GEMINI_API_KEY=<PASTE_KEY>,GEMINI_MODEL=gemini-3.5-flash,USE_MOCK_BIGQUERY=true"
```

Notes:
- `--source .` builds from the repo Dockerfile via Cloud Build — no local Docker needed.
- Do NOT set `GOOGLE_CLOUD_PROJECT` / `GOOGLE_CLOUD_LOCATION` in env vars; with an
  AI Studio key they break auth (same gotcha as `.env`, see PR #3).
- Add `FRONTEND_ORIGINS=<frontend-url>` to `--set-env-vars` AFTER the frontend is
  deployed (step 2), then redeploy — ADK's origin-check middleware rejects unknown
  origins.
- Grab the URL: `gcloud run services describe patent-agent --region us-central1 --format 'value(status.url)'`

Smoke test: `curl "<url>/api/landscape?query=solid+electrolyte&domain=batteries" | head -c 300`

## 2. Frontend → static hosting (free)

```bash
cd frontend
echo "VITE_API_BASE_URL=<cloud-run-url>" > .env.production.local
npm run build
npx vercel deploy --prod        # or: npx netlify-cli deploy --prod --dir=dist
```

Then redeploy the backend with `FRONTEND_ORIGINS` set to the frontend URL (see step 1).

## 3. Quota reality check

Free tier: **5 req/min and 20 req/day per model.** One full graph run ≈ 20 calls,
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
