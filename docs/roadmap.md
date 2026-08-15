# Roadmap — Patent Innovation Agent

**Hackathon:** All Things Agentic Hackathon (Devpost, Google-sponsored)
**Track:** The Taskmaster — "build a complete workflow, not just a chatbot... make one that takes action."
**Deadline:** Sept 1, 2026, 2:00am GMT+2
**Start date:** Aug 15, 2026 — **15 days**

This roadmap replaces the original 24-48h hackathon-sprint scope with a 15-day plan: recover the full original architecture (4 agents + landscape mining + governor scoring), but sequence it so nothing is late and the last two days are protected for rehearsal, not development.

---

## 1. Mandatory requirements checklist

Every submission to this hackathon must satisfy all of these — keep this list current through Day 15:

- [ ] **Gemini 3.5+** used via Gemini API or Vertex AI (pinned in `backend/patent_agent/config.py`)
- [ ] **Google Agent Framework**: Google ADK (Python) — all 4 agents + orchestration built on it
- [ ] **Google Cloud infra service**: Cloud Run (deployed backend); BigQuery also counts as a second infra service once wired to real credentials
- [ ] Hosted project URL (Cloud Run service URL, once deployed)
- [ ] Text description (features, functionality, technologies used, other data sources, findings/learnings)
- [ ] Public or private code repo (if private: share with `testing@devpost.com` and `cloudhackathons@google.com`)
- [ ] `README.md` with reproducible spin-up instructions
- [ ] Architecture diagram (see `docs/architecture.md`)
- [ ] ~4 min demo video that **visibly shows the backend running on Google Cloud** (Cloud Run dashboard, Vertex AI logs, or the `.run.app` URL — not just localhost)

Optional bonus points (not required, worth considering only if Days 14-15 have slack): public blog/video about the build process; social post with `#AllThingsAgenticHackathon`; integrating another Google AI model (Gemma/Veo/Lyria) — low priority, cut first if time is tight.

---

## 2. Scope lock (Day 1, highest-risk unscoped decision)

Everything downstream depends on picking **one concrete technology domain** for the demo (e.g. "solid-state battery electrolytes," "mRNA delivery lipids," a domain the team can sanity-check without being domain experts). This must be locked by end of Day 1 — do not let it drift past Day 3, since the clustering/white-space work in Days 4-6 is meaningless without a fixed corpus to mine.

_Domain chosen: **(fill in Day 1)**_

---

## 3. Day-by-day plan

### Days 1-3 — Data + Research Agent
- Lock the demo domain (see §2).
- Stand up `research_agent` (ADK `LlmAgent`) with BigQuery-backed tools (`search_patents`, `get_patent_by_number`, `get_citations`, `get_similar_patents`) against `patents-public-data.patents.publications` and `google_patents_research.publications`.
- Ship against the **mock** `PatentsDataSource` first (`USE_MOCK_BIGQUERY=true`) — no GCP credentials needed to keep developing. Swap to real BigQuery the moment credentials exist, no code changes required elsewhere.
- Decide the literature-search source (e.g. Semantic Scholar or arXiv API) — stub it the same way as BigQuery if credentials/rate limits are a blocker.
- **Definition of done:** `research_agent` returns a structured `patent_landscape` (list of `PatentRecord`) for the locked domain, backed by mock or real data, callable end-to-end via `adk web`.

### Days 4-6 — Landscape + Technology Graph
- Add a clustering `FunctionTool` (embeddings + e.g. HDBSCAN/KMeans) that `research_agent` calls — **not a 5th LLM agent**, this is a deterministic step.
- Define the saturated-area vs. white-space heuristic (e.g. cluster density + recency + citation velocity).
- Freeze the output schema (cluster → representative patents → white-space score) by end of Day 6 so the frontend (Days 12-13) has a stable contract to build against.
- **Definition of done:** given the locked domain, the pipeline outputs a ranked list of white-space clusters with supporting patent IDs — this is the visual/narrative backbone of the whole demo.

### Days 7-9 — Inventor Agent + Adversarial Agent
- **Named milestone, before starting this phase:** validate the leading white-space candidate with a domain-knowledgeable person (even informally) — the risk being called out explicitly is discovering on Day 12 that the "discovery" is already patented.
- Build `inventor_agent` (proposes candidate inventions from a white-space cluster) and `adversarial_agent` (attacks each candidate using prior art, must cite the specific patents it used).
- Wire them as an ADK `LoopAgent` (propose → critique → repeat) so multiple prompt iterations and curation passes happen automatically instead of ad hoc reruns; adversarial agent calls `exit_loop` when a candidate survives scrutiny or `max_iterations` is hit.
- Iterate the Inventor prompt multiple times — with 15 days there's room to actually curate which candidates are interesting instead of accepting the first output.
- **Definition of done:** for the locked domain, the loop produces at least 3-5 candidate inventions with attached adversarial verdicts (accept/reject + cited patents) via `adk web`.

### Days 10-11 — Innovation Governor
- Build `governor_agent`: scores surviving candidates on **novelty, prior-art risk, differentiation, evidence** — every score must cite concrete `publication_number`s in `supporting_evidence`, never a bare number. This is where "Architectural Discipline" (30% of judging) is won or lost.
- **Definition of done:** `governor_agent` outputs a `ScoreCard` per candidate with all 4 sub-scores and non-empty evidence citations, consumable directly by the frontend.

### Days 12-13 — UX / Visualization (Lydia)
- Backend endpoints **frozen at the start of Day 12** — no schema changes during frontend work.
- Build the Invention Opportunity Map (React + Vite) — the landscape clusters plotted with white-space candidates surfaced, plus the researcher interaction flow.
- Wire the "explain your reasoning" toggle (see §4).
- **Definition of done:** a researcher can pick a cluster, see candidate inventions, see their scores, and expand "why" to see the cited patents behind both the adversarial verdict and the governor score.

### Days 14-15 — Demo rehearsal, script, buffer
- Reserved unconditionally — this is what gets cut first when development overruns, and it's what most penalizes the final presentation.
- Write the demo script (~4 min), rehearse live (not just "should work"), deploy hardening on Cloud Run, bug-fix buffer, record the demo video, finalize `docs/architecture.md` diagram, finish README, submission checklist (§5) pass.

---

## 4. Explainability feature spec

The Adversarial Agent's `AdversarialVerdict.cited_patents` and the Governor's `ScoreCard.supporting_evidence` are both required, structured fields (not optional, not free text) — see `backend/patent_agent/tools/schemas.py`. The frontend's "explain" toggle on each candidate simply renders these lists as linked patent references. This is what separates a demo built on "magic LLM outputs" from one a technical judge can actually verify — the reasoning is traceable to specific documents, not just an LLM's say-so.

---

## 5. Submission checklist

- [ ] Repo shared with `testing@devpost.com` and `cloudhackathons@google.com` if kept private
- [ ] Demo video (~4 min): problem statement, value proposition, live demo, **visible proof of Cloud Run / Google Cloud usage**
- [ ] Text description drafted (features, tech used, other data sources, findings/learnings)
- [ ] Track-justification paragraph (why "The Taskmaster" fits)
- [ ] Architecture diagram finalized and embedded in README
- [ ] README spin-up instructions verified by literally following them on a clean checkout

---

## 6. Open risks / decisions log

| Decision | Options | Owner | Due |
|---|---|---|---|
| Demo domain | TBD | — | Day 1 |
| Literature source (beyond patents) | Semantic Scholar API / arXiv API / skip | — | Day 3 |
| Firestore for persisted scorecards | Add vs. skip (session state may be enough for a demo) | — | Day 10 |
| Cloud Run deploy path | `adk deploy cloud_run` (fast) vs. manual Dockerfile + `gcloud run deploy` (more transparent, chosen for the initial scaffold) | — | Day 14 |
| Domain-expert validation of chosen white space | Who / how | — | Before Day 7 |
