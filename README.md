# Patent Innovation Agent

_Finds patentable white-space opportunities by mining patent landscapes, proposing candidate inventions, stress-testing them against prior art, and scoring the survivors with traceable evidence._

Built for the **Devpost "All Things Agentic Hackathon"** (Google Cloud / Gemini) — track: **The Taskmaster**.

> Status: Live deployed on Google Cloud Run at [`https://patent-agent-873418702379.us-central1.run.app`](https://patent-agent-873418702379.us-central1.run.app). Full agent graph (research → inventor/adversarial loop → governor) live-validated. Async `/api/analyze` job endpoint wired into OpportunityMap frontend. CI (pytest + tsc/vite/oxlint) passing on every push/PR. See [`docs/roadmap.md`](docs/roadmap.md) and [`docs/architecture.md`](docs/architecture.md).

## Architecture

See [`docs/architecture.md`](docs/architecture.md) for the full component breakdown and diagram.

## Features

- ✅ Patent landscape search + CPC-prefix clustering with a white-space score (density + recency + citation velocity + demand), exposed at `GET /api/landscape` — live on Cloud Run.
- ✅ Frontend `OpportunityMap` renders that landscape live: search, expandable cluster cards, and candidate/scorecard drill-down with cited prior art.
- ✅ Full agent graph (research → inventor/adversarial loop → governor) Gemini-backed and live-validated.
- ✅ `POST /api/analyze` background job execution with `GET /api/analyze/{job_id}` polling.
- ✅ CI (GitHub Actions) runs backend `pytest` and frontend `tsc`/`vite build`/`oxlint` on every push and PR.
- ✅ Deployed live on Google Cloud Run (`us-central1`).

## Tech stack

| Layer | Choice |
|---|---|
| LLM | Gemini 3.5 (Gemini API or Vertex AI) |
| Agent framework | [Google ADK](https://google.github.io/adk-docs/) (Python) |
| Patent data | Google Patents Public Datasets (BigQuery), mocked locally by default |
| Cloud infra | Cloud Run |
| Frontend | React + Vite (TypeScript) |

## Prerequisites

- Python 3.11+
- Node.js 20+
- (optional, for real BigQuery/Cloud Run) [`gcloud` CLI](https://cloud.google.com/sdk/docs/install) authenticated against a GCP project

## Setup / spin-up

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example .env   # defaults to USE_MOCK_BIGQUERY=true, no GCP credentials required
adk web patent_agent      # or: uvicorn main:app --reload --port 8080
```

### Frontend

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

## Environment variables

See [`.env.example`](.env.example) for the full list (Gemini model/key, GCP project/location, `USE_MOCK_BIGQUERY` toggle, port).

## Deploying to Cloud Run

Quick path:

```bash
adk deploy cloud_run --project=$GOOGLE_CLOUD_PROJECT --region=$GOOGLE_CLOUD_LOCATION backend/patent_agent
```

Manual path (Dockerfile-based, used for local image verification too):

```bash
docker build -t patent-agent-backend backend/
gcloud run deploy patent-agent-backend \
  --image patent-agent-backend \
  --project $GOOGLE_CLOUD_PROJECT \
  --region $GOOGLE_CLOUD_LOCATION \
  --allow-unauthenticated
```

## Demo video

_(link added Day 15)_

## Team

- Backend / agents: _(fill in)_
- UX / frontend: Lydia

## License

_(fill in)_
