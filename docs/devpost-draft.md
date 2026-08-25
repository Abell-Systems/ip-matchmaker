# Devpost Submission Draft — IP Matchmaker

**Project Name:** IP Matchmaker (Patent Innovation Agent)  
**Tagline:** Autonomous R&D intelligence matching industry tech calls with patent white-space opportunities using Google ADK & Gemini 3.5.  
**Track:** The Taskmaster ("Build a complete workflow, not just a chatbot... make one that takes action.")  

---

## 1. One-Line Pitch
IP Matchmaker mines global patent landscapes and market-pull technology calls, autonomously generating, stress-testing, and scoring patentable inventions with traceable prior-art evidence.

---

## 2. The Problem
R&D teams face a dual challenge: industry technology calls (e.g. Innoget, SBIR) express urgent market demand, but existing patent landscapes are dense, complex, and hard to navigate. Traditional search tools return endless lists of keywords without identifying true white space or verifying whether proposed solutions conflict with prior art.

---

## 3. The Solution
IP Matchmaker provides an end-to-end autonomous R&D workflow:
1. **Market-Pull Ingestion**: Parses open technology calls (Innoget dataset) into structured `DemandSignal` objects.
2. **Patent Landscape Clustering**: Queries Google Patents Public Datasets on BigQuery and scores technology clusters using a quantitative white-space formula ($0.40 \cdot \text{density} + 0.20 \cdot \text{recency} + 0.15 \cdot \text{citation\_velocity} + 0.25 \cdot \text{demand}$).
3. **Autonomous Invention Loop**: An **Inventor Agent** proposes candidate inventions for white-space gaps, while an **Adversarial Agent** stress-tests them against prior art, forcing iterative refinement.
4. **Innovation Governor & Traceability**: An **Innovation Governor Agent** scores surviving candidates across novelty, prior-art risk, differentiation, and evidence, backing every score with exact patent publication numbers.

---

## 4. Technical Architecture

```text
[Innoget Tech Calls] ──> [InnogetDemandDataSource] ──┐
                                                    ├──> [clustering.py] ──> [OpportunityMap UI]
[Google Patents / BQ] ──> [PatentsDataSource] ──────┘           │
                                                                ▼
                                                [POST /api/analyze (ADK Runner)]
                                                                │
                                            ┌───────────────────┴───────────────────┐
                                            ▼                                       ▼
                                   [research_agent]                         [governor_agent]
                                            │                                       ▲
                                            ▼                                       │
                                 [invention_loop (LoopAgent)] ──────────────────────┘
                                 ├── inventor_agent (proposes)
                                 └── adversarial_agent (critiques + cites prior art)
```

- **Agent Framework**: Built using **Google ADK** (Python), composing `LlmAgent`, `SequentialAgent`, and nested `LoopAgent`.
- **LLM Engine**: Powered by **Gemini 3.5** (`gemini-3.5-flash` / `gemini-3.5-flash-lite`).
- **Data Layer**: Google Patents Public Datasets on BigQuery + Innoget Technology Calls feed.
- **Frontend**: React + Vite (TypeScript) rendering the interactive `OpportunityMap` with live background-job polling (`POST /api/analyze` $\rightarrow$ `202 Job Accepted` $\rightarrow$ `GET /api/analyze/{job_id}`).
- **Infrastructure**: Cloud Run containerized deployment (`backend/Dockerfile`).

---

## 5. Why "The Taskmaster"?
IP Matchmaker is not a conversational chatbot. It takes direct action:
- Executes multi-step search & landscape clustering queries.
- Runs an autonomous propose-critique loop where agents challenge each other using real patent citations.
- Outputs actionable, traceable `ScoreCard` artifacts that R&D directors can use immediately for patent filings or technology licensing decisions.

---

## 6. Example Finding & Validation
In our live validation run on solid-state battery electrolytes:
- **Input Domain**: Solid-state electrolytes for EV batteries.
- **Market Demand**: Innoget technology call for high-conductivity, stable interface coatings.
- **White-Space Cluster**: `cluster-C08L` (Polymer compositions / interfacial buffer layers).
- **Candidate Invention**: *"Zwitterionic Polyimide MLD Interfacial Buffer Layer"*.
- **Adversarial Verdict**: Rejected initial draft citing 4 prior-art publication numbers (`US-10448361-B2-17`, `US-10437821-B2-0`), prompting the Inventor agent to refine the chemical composition.
- **Governor ScoreCard**: Novelty 0.92, Prior-Art Risk 0.85, Differentiation 0.88, Evidence 0.95, backed by traceable citations.

---

## 7. Setup & Reproducibility

```bash
# Clone & install backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example .env

# Run full test suite (41/41 tests passing)
PYTHONPATH=. pytest tests/ -v

# Run interactive ADK Web UI or FastAPI server
adk web patent_agent
# or: uvicorn main:app --reload --port 8080
```

```bash
# Frontend setup
cd frontend
npm install
npm run dev
```

---

## 8. Infrastructure Cost & Resource Estimation
> **Estimated demo infrastructure cost: $0.**
> The prototype is designed to run within the applicable Google Cloud and Gemini free-tier quotas. Cloud Run provides a monthly free tier for low-volume workloads, and the demo's expected usage is substantially below those limits. Gemini usage is likewise intended to remain within the applicable free-tier quota. No paid infrastructure is required for the expected hackathon demonstration workload.
>
> A Google Cloud project and billing-enabled account may be required to deploy Cloud Run. Actual charges depend on current Google Cloud pricing, quotas, region, and account configuration.

---

## 9. Team & Links
- **Code Repository**: [GitHub Repository](https://github.com/Abell-Systems/ip-matchmaker)
- **Hosted App**: [https://patent-agent-873418702379.us-central1.run.app](https://patent-agent-873418702379.us-central1.run.app)
- **Demo Video**: [YouTube / Vimeo Link]
