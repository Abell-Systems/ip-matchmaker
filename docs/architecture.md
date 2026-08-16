# Architecture

> Placeholder — the actual diagram (image, exported from e.g. Excalidraw/draw.io as PNG/SVG into this folder and embedded below) is due **Day 13-14** per `docs/roadmap.md`. This document defines exactly what it must show so nothing gets improvised at the last minute.

## Components the diagram must include

- **Frontend** — React + Vite SPA (Invention Opportunity Map, researcher interaction flow)
- **Cloud Run service** — hosts the FastAPI wrapper (`backend/main.py`) around the ADK Runner
- **The 4 agents + orchestration boundary**:
  - `research_agent` (Days 1-3)
  - clustering `FunctionTool` used by `research_agent` (Days 4-6, deterministic — not a 5th LLM agent)
  - `invention_loop` = `LoopAgent([inventor_agent, adversarial_agent])` (Days 7-9)
  - `governor_agent` (Days 10-11)
  - composed by a root `SequentialAgent`
- **BigQuery Patents Public Datasets** — `patents-public-data.patents.publications` / `google_patents_research.publications` (real), with the mock/real swap point (`USE_MOCK_BIGQUERY`) explicitly called out — this doubles as evidence for judges that the system was designed for real credentials, just not blocked by their absence during development
- **Demand-signal sources** — SBIR.gov Topic API / CORDIS Data Extraction Tool API (open technology-need feeds), same mock/real swap pattern (`USE_MOCK_DEMAND`), feeding `white_space_score` as a market-pull term alongside patent supply-side signals
- **Gemini API / Vertex AI** — the LLM backing every `LlmAgent`
- **Session/state store** — ADK session state (in-memory/dev), noting whether Firestore gets added for persisted scorecards (open decision, see roadmap §6)

## Data flow narrative

```
User query (domain/prompt)
  → research_agent (BigQuery tool: search/get/cite/similar patents)
  → clustering FunctionTool (CPC-prefix grouping + demand-signal lookup (SBIR/CORDIS) → white-space clusters)
  → invention_loop:
       inventor_agent (propose candidate) ⇄ adversarial_agent (attack w/ cited prior art)
       repeats until adversarial_agent calls exit_loop or max_iterations
  → governor_agent (novelty / prior-art risk / differentiation / evidence scoring,
                     each score backed by supporting_evidence patent citations)
  → frontend Invention Opportunity Map (cluster view → candidates → scores → "explain" drill-down)
```

## Shared state table

| State key | Producer | Consumer(s) |
|---|---|---|
| `patent_landscape` | `research_agent` | clustering tool, `inventor_agent` |
| `candidate_inventions` | `inventor_agent` | `adversarial_agent`, `governor_agent`, frontend |
| `adversarial_verdicts` | `adversarial_agent` | `inventor_agent` (next loop iteration), `governor_agent`, frontend |
| `scored_candidates` | `governor_agent` | frontend |

(Exact key names live in `backend/patent_agent/shared/state_keys.py` as the single source of truth — this table must stay in sync with that file.)

## Deployment topology

- Single Cloud Run service serving the FastAPI + ADK runtime (backend).
- Frontend hosting: **TBD** — either served as static assets from the same Cloud Run service, or deployed separately (Firebase Hosting / Cloud Run static). Decide Day 12 alongside the frontend freeze.
- Region: `us-central1` (default, see `.env.example`).

## Diagram TODO

- [ ] Produce the actual diagram image (Excalidraw/draw.io export) — target Day 13-14
- [ ] Embed it in this file and link from `README.md`
