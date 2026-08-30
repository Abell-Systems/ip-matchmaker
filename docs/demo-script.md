# Demo Video Script — IP Matchmaker

**Duration:** ~4 minutes (Live / Unedited Action Flow)  
**Track:** The Taskmaster (Devpost "All Things Agentic Hackathon")  
**Locked Domain:** *"Solid-state electrolytes for EV batteries"*  

---

## Timed Video Script (4:00 Total)

```text
0:00–0:30  Problema & Context
0:30–1:00  Input & Problem Formulation
1:00–1:40  Landscape Mining & White-Space Detection
1:40–2:30  Agent Working (Research & Inventor Proposal)
2:30–3:15  Adversarial Rejection & Inventor Iteration Loop
3:15–3:40  Final Invention & Traceable Evidence ScoreCard
3:40–4:00  Cloud Run & Google Cloud Live Infrastructure Proof
```

---

## Breakdown & Voiceover Guide

### 0:00 – 0:30 | Problema (Problem Statement)
- **Visual:** Split screen: Massive, dense patent database listings vs. R&D teams searching manually for freedom-to-operate white spaces.
- **Voiceover:**
  > "Finding genuine, patentable white-space opportunities is like finding a needle in a haystack. Traditional keyword search tools return thousands of dense patents, leaving researchers to manually guess prior-art risks."

### 0:30 – 1:00 | Input (Domain Selection)
- **Visual:** User inputs query *"solid-state electrolytes"* and domain *"EV batteries"* in the IP Matchmaker UI.
- **Voiceover:**
  > "Meet IP Matchmaker: an autonomous R&D intelligence agent built on Google ADK, Gemini 3.5, and Google Cloud BigQuery. We start by specifying a technical domain—solid-state electrolytes for EV batteries—combining supply-side patents with a market-demand signal."

### 1:00 – 1:40 | Landscape + White-Space
- **Visual:** The execution view shows the pipeline stages advancing live. Highlight the white-space cluster ("Solid Electrolytes - Sulfide & Oxide Interfaces") and its `white_space_score` once results land.
- **Voiceover:**
  > "Our landscape engine mines Google Patents Public Datasets on BigQuery, groups patents by CPC classification, and calculates a quantitative white-space score combining density, recency, citation velocity, and market demand. Clusters highlighted in green reveal true innovation white spaces."

### 1:40 – 2:30 | Agent Working
- **Visual:** Clicking "Analyze White Space" triggers `POST /api/analyze`. Status changes to `running`. The **Inventor Agent** generates `InventionCandidate` (candidate_id: `c1-inv-1`).
- **Voiceover:**
  > "When a white space is selected, IP Matchmaker launches an autonomous multi-agent pipeline. Our **Inventor Agent** analyzes the cluster and proposes a novel candidate invention: a gradient sulfide-halide solid electrolyte interface to prevent dendrite growth."

### 2:30 – 3:15 | Adversarial Rejection + Iteration
- **Visual:** **Adversarial Agent** evaluates proposal, emits verdict `"rejected"`, citing prior art `US-10448361-B2`. **Inventor Agent** receives rejection and auto-iterates, creating refined candidate `c1-inv-2` with a fluorinated interphase. **Adversarial Agent** re-evaluates and emits `"survives"`.
- **Voiceover:**
  > "Next, our **Adversarial Agent** attacks the proposal against prior art. It finds an overlapping patent—US-10448361-B2—and rejects candidate 1 with detailed rationale. Rather than giving up, the Inventor Agent ingests the rejection, iterates, and proposes candidate 2 with a specialized fluorinated protective interphase. The Adversarial Agent re-tests and confirms it survives prior art scrutiny."

### 3:15 – 3:40 | Final Invention + Evidence
- **Visual:** Final `ScoreCard` renders with sub-scores: Novelty (0.92), Prior-Art Risk (0.85), Differentiation (0.88), Evidence (0.95). Expanding `supporting_evidence` shows clickable prior-art publication IDs.
- **Voiceover:**
  > "Finally, our **Innovation Governor Agent** evaluates the surviving candidate. It outputs a complete ScoreCard where every single score is backed by traceable patent publication numbers—providing concrete evidence, not LLM hallucinations."

### 3:40 – 4:00 | Cloud Run / Google Cloud Proof
- **Visual:** Browser showing live backend URL on Cloud Run (`https://patent-agent-...run.app/health`) and Google Cloud Console dashboard with active Cloud Run service logs.
- **Voiceover:**
  > "IP Matchmaker runs live on Google Cloud Run, leveraging Gemini 3.5 and BigQuery. This is autonomous innovation intelligence ready for production. Thank you!"

---

## Recording Golden Rules

1. **Unedited Action:** Show actual agent responses and UI state transitions without skipping steps.
2. **Cloud Run Visibility:** Keep Google Cloud Console / Cloud Run URL visible on screen at the 3:40 mark to fulfill GCP proof criteria.
