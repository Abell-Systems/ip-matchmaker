# Demo Video Script — IP Matchmaker

**Duration:** ~4 minutes  
**Track:** The Taskmaster (Devpost "All Things Agentic Hackathon")  
**Core Story:** *"There is demand for a technology. Where is the white space, what could we build, and should we pursue it?"*

---

## Script Breakdown

### 0:00 – 0:30 | Problem Statement
- **Visual:** Split screen or slide showing open innovation requests (Innoget) vs. massive, dense patent databases (Google Patents / BigQuery).
- **Voiceover:**
  > "Every year, R&D organizations publish thousands of open technology demands searching for solutions. At the same time, millions of patents saturate existing technical domains. Finding genuine innovation opportunities—where market pull meets true patent white space—is like finding a needle in a haystack. Current search tools return bare keyword lists, leaving researchers to manually decipher prior art risks."

### 0:30 – 1:10 | Input & Market Demand Signal
- **Visual:** Focus on an active technology call from the Innoget feed (e.g. *"PFAS-free Low-Friction Coating for metallic cutting edges"* or *"Solid-state electrolyte interface"*). Show how IP Matchmaker ingests open tech calls into structured `DemandSignal` objects.
- **Voiceover:**
  > "Meet IP Matchmaker: an autonomous Patent Innovation Agent built on Google ADK and Gemini 3.5. We start with real market-pull signals—here, an open technology call seeking low-friction, durable coatings. IP Matchmaker ingests these calls and queries Google Patents Public Datasets to map the entire competitive landscape."

### 1:10 – 2:00 | OpportunityMap & White-Space Discovery
- **Visual:** Screen recording of the React + Vite frontend (`OpportunityMap`). Show search execution (`coating`, `materials` or `solid electrolyte`, `EV batteries`). Expand cluster cards showing patent count, recency, citation velocity, Innoget demand signals, and the `white_space_score`.
- **Voiceover:**
  > "Our landscape engine groups patents by CPC technology prefix and computes a quantitative white-space score: combining patent density, recency, citation velocity, and market demand signals. In our OpportunityMap, clusters highlighted in green represent true white space—low patent saturation combined with strong industry demand."

### 2:00 – 3:10 | Autonomous Agent Loop (Inventor $\rightarrow$ Adversarial)
- **Visual:** Trigger `POST /api/analyze` on a white-space cluster. Display live status polling. Show `Inventor` agent output proposing candidate invention (`InventionCandidate`), followed by `Adversarial` agent's critique citing 4 exact prior-art publication numbers (`US-10448361-B2-17`), causing the `Inventor` agent to iterate.
- **Voiceover:**
  > "Once a white-space cluster is selected, IP Matchmaker launches an autonomous multi-agent graph. First, our **Inventor Agent** proposes a candidate invention targeting the gap. Next, our **Adversarial Agent** stress-tests the proposal against prior art. It actively attacks the candidate, citing specific patent publication numbers. If prior art overlaps, the Inventor agent refines the proposal automatically until it survives scrutiny."

### 3:10 – 3:45 | Innovation Governor & Evidence Traceability
- **Visual:** Show final `ScoreCard` rendered in the UI with sub-scores (Novelty: 0.92, Prior-Art Risk: 0.85, Differentiation: 0.88, Evidence: 0.95). Expand the "Explain Reasoning" toggle to show linked publication numbers in `supporting_evidence`.
- **Voiceover:**
  > "Finally, our **Innovation Governor Agent** evaluates surviving candidates, generating a comprehensive ScoreCard across novelty, risk, differentiation, and evidence. Crucially, every single score is backed by traceable patent publication numbers—not LLM hallucinations. Researchers can click any score to verify the exact prior art backing the decision."

### 3:45 – 4:00 | Closing & Value Proposition
- **Visual:** Overview of full flow (Innoget $\rightarrow$ Landscape $\rightarrow$ Agent Loop $\rightarrow$ ScoreCard) with Cloud Run / Google Cloud dashboard proof.
- **Voiceover:**
  > "IP Matchmaker connects market pull with patent landscape intelligence, turning evidence into actionable innovation decisions. Powered by Google ADK, Gemini 3.5, and Google Cloud, this is autonomous R&D intelligence at scale. Thank you!"

---

## Production Notes & Verification Checklist

- [ ] Record in 1080p, 60fps with clear audio.
- [ ] Show Cloud Run backend URL (`.run.app`) or Google Cloud console dashboard visibly in the background to satisfy GCP usage judging criteria.
- [ ] Keep agent loop section focused on *what changes* (candidate refinement + prior art citations), not internal framework code.
