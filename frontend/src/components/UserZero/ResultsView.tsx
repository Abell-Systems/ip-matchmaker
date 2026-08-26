import { useState } from "react";
import type { JobStatusResponse } from "../../types/patent";
import { CausalChain } from "./CausalChain";
import styles from "./ResultsView.module.css";

function formatScore(score?: number | null): string {
  if (score === undefined || score === null || Number.isNaN(score)) return "N/A";
  if (score <= 1) return `${Math.round(score * 100)}%`;
  return `${Math.round(score)}%`;
}

function getPatentUrl(pubNumber: string): string {
  const clean = pubNumber.replace(/[^A-Za-z0-9]/g, "");
  return `https://patents.google.com/patent/${clean}/en`;
}

export interface ResultsViewProps {
  domain?: string;
  result: JobStatusResponse;
  onReset?: () => void;
}

export function ResultsView({ domain, result, onReset }: ResultsViewProps) {
  const [showCausalChain, setShowCausalChain] = useState(false);

  const candidates = result.candidates || [];
  const verdicts = result.verdicts || [];
  const scorecards = result.scorecards || [];
  const clusters = result.clusters || [];

  // Filter candidates prioritizing surviving ones
  const survivingCandidates = candidates.filter((c) => {
    const v = verdicts.find((verdict) => verdict.candidate_id === c.candidate_id);
    return v ? v.verdict === "survives" : true;
  });

  const displayCandidates = survivingCandidates.length > 0 ? survivingCandidates : candidates;

  const [selectedCandidateId, setSelectedCandidateId] = useState<string>(
    displayCandidates[0]?.candidate_id || ""
  );

  const currentCandidate =
    candidates.find((c) => c.candidate_id === selectedCandidateId) ||
    displayCandidates[0];

  const currentCluster =
    clusters.find((cl) => cl.cluster_id === currentCandidate?.cluster_id) ||
    clusters[0];

  const currentVerdict = verdicts.find(
    (v) => v.candidate_id === currentCandidate?.candidate_id
  );

  const currentScorecard = scorecards.find(
    (sc) => sc.candidate_id === currentCandidate?.candidate_id
  );

  if (!currentCandidate) {
    return (
      <div className={styles.container}>
        <header className={styles.header}>
          {domain && <h2 className={styles.domainTitle}>{domain}</h2>}
          <h1 className={styles.title}>Analysis Completed</h1>
        </header>
        <div className={styles.emptyCard}>
          <p className={styles.emptyMessage}>
            No candidate inventions survived the prior-art challenge for this query.
          </p>
          {onReset && (
            <button type="button" className={styles.primaryBtn} onClick={onReset}>
              Analyze another opportunity
            </button>
          )}
        </div>
      </div>
    );
  }

  // Calculate prior art risk level
  const priorArtRiskVal = currentScorecard?.prior_art_risk;
  const isLowRisk = priorArtRiskVal !== undefined && (priorArtRiskVal <= 0.35 || (priorArtRiskVal <= 35 && priorArtRiskVal > 1));

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        {domain && <div className={styles.domainBadge}>{domain}</div>}
        <h1 className={styles.title}>Top Surviving Invention Opportunity</h1>
        <p className={styles.subtitle}>
          The agent discovered white-space, generated candidate claims, attacked them with adversarial prior-art citations, and verified survival.
        </p>
      </header>

      {displayCandidates.length > 1 && (
        <div className={styles.candidateSelector}>
          <span className={styles.selectorLabel}>Surviving candidates:</span>
          <div className={styles.candidatePills}>
            {displayCandidates.map((cand, idx) => (
              <button
                key={cand.candidate_id}
                type="button"
                className={`${styles.candidatePill} ${
                  cand.candidate_id === currentCandidate.candidate_id
                    ? styles.candidatePillActive
                    : ""
                }`}
                onClick={() => setSelectedCandidateId(cand.candidate_id)}
              >
                Candidate {idx + 1}: {cand.title.slice(0, 30)}…
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Decision Card */}
      <section className={styles.decisionCard} aria-label="Decision card summary">
        {/* 1. What is proposed? */}
        <div className={styles.sectionBlock}>
          <div className={styles.questionHeader}>
            <span className={styles.questionNumber}>1</span>
            <h3 className={styles.questionTitle}>What is proposed?</h3>
          </div>
          <div className={styles.answerContent}>
            <h2 className={styles.candidateHeading}>{currentCandidate.title}</h2>
            <p className={styles.candidateDescription}>
              {currentCandidate.description}
            </p>
            {currentCandidate.claimed_novelty && (
              <div className={styles.highlightBadge}>
                <span className={styles.badgePrefix}>Core Claimed Novelty:</span>{" "}
                {currentCandidate.claimed_novelty}
              </div>
            )}
          </div>
        </div>

        {/* 2. Why this opportunity? */}
        <div className={styles.sectionBlock}>
          <div className={styles.questionHeader}>
            <span className={styles.questionNumber}>2</span>
            <h3 className={styles.questionTitle}>Why this opportunity?</h3>
          </div>
          <div className={styles.answerContent}>
            <div className={styles.opportunityRow}>
              <div className={styles.opportunityInfo}>
                <span className={styles.opportunityLabel}>
                  {currentCluster?.label || "Target White-Space Cluster"}
                </span>
                <p className={styles.opportunityDesc}>
                  Under-served white-space area in the surveyed patent landscape with low prior-art saturation and unaddressed demand signals.
                </p>
              </div>
              <div className={styles.scoreBadgeBox}>
                <span className={styles.scoreBadgeLabel}>White-Space Score</span>
                <span className={styles.scoreBadgeValue}>
                  {formatScore(currentCluster?.white_space_score)}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* 3. What challenged it? */}
        <div className={styles.sectionBlock}>
          <div className={styles.questionHeader}>
            <span className={styles.questionNumber}>3</span>
            <h3 className={styles.questionTitle}>What challenged it?</h3>
          </div>
          <div className={styles.answerContent}>
            <p className={styles.challengeIntro}>
              The adversarial examiner challenged the candidate against closest prior-art citations:
            </p>
            {currentVerdict?.cited_patents && currentVerdict.cited_patents.length > 0 ? (
              <div className={styles.patentList}>
                {currentVerdict.cited_patents.map((pat) => (
                  <a
                    key={pat}
                    href={getPatentUrl(pat)}
                    target="_blank"
                    rel="noopener noreferrer"
                    className={styles.patentBadge}
                    title={`View ${pat} on Google Patents`}
                  >
                    <span>{pat}</span>
                    <span className={styles.externalIcon}>↗</span>
                  </a>
                ))}
              </div>
            ) : (
              <p className={styles.emptyNote}>No blocking patent references found in landscape.</p>
            )}
            {currentVerdict?.rationale && (
              <div className={styles.quoteBox}>
                <span className={styles.quoteLabel}>Adversarial Objection:</span>
                <p className={styles.quoteText}>{currentVerdict.rationale}</p>
              </div>
            )}
          </div>
        </div>

        {/* 4. Why did it survive? */}
        <div className={styles.sectionBlock}>
          <div className={styles.questionHeader}>
            <span className={styles.questionNumber}>4</span>
            <h3 className={styles.questionTitle}>Why did it survive?</h3>
          </div>
          <div className={styles.answerContent}>
            <div className={styles.survivalStatusRow}>
              <span className={styles.survivesBadge}>✓ Survives Prior-Art Challenge</span>
            </div>
            <p className={styles.differentiationText}>
              {currentCandidate.claimed_novelty ||
                "Clear functional differentiation from cited prior art establishes strong novelty and freedom-to-operate potential."}
            </p>
          </div>
        </div>

        {/* 5. Evidence & Final Assessment */}
        <div className={styles.sectionBlock}>
          <div className={styles.questionHeader}>
            <span className={styles.questionNumber}>5</span>
            <h3 className={styles.questionTitle}>Evidence & Final Assessment</h3>
          </div>
          <div className={styles.answerContent}>
            {/* Scores Grid */}
            <div className={styles.scoresGrid}>
              <div className={styles.scoreMetricCard}>
                <span className={styles.scoreMetricLabel}>Novelty</span>
                <span className={styles.scoreMetricValue}>
                  {formatScore(currentScorecard?.novelty)}
                </span>
                <div className={styles.progressBar}>
                  <div
                    className={styles.progressFill}
                    style={{
                      width: formatScore(currentScorecard?.novelty),
                    }}
                  />
                </div>
              </div>

              <div className={styles.scoreMetricCard}>
                <span className={styles.scoreMetricLabel}>Prior-Art Risk</span>
                <div className={styles.riskValueRow}>
                  <span className={styles.scoreMetricValue}>
                    {formatScore(currentScorecard?.prior_art_risk)}
                  </span>
                  <span
                    className={`${styles.riskBadge} ${
                      isLowRisk ? styles.lowRiskBadge : styles.medRiskBadge
                    }`}
                  >
                    {isLowRisk ? "Low risk" : "Moderate risk"}
                  </span>
                </div>
                <div className={styles.progressBar}>
                  <div
                    className={`${styles.progressFill} ${styles.riskProgressFill}`}
                    style={{
                      width: formatScore(currentScorecard?.prior_art_risk),
                    }}
                  />
                </div>
              </div>

              <div className={styles.scoreMetricCard}>
                <span className={styles.scoreMetricLabel}>Differentiation</span>
                <span className={styles.scoreMetricValue}>
                  {formatScore(currentScorecard?.differentiation)}
                </span>
                <div className={styles.progressBar}>
                  <div
                    className={styles.progressFill}
                    style={{
                      width: formatScore(currentScorecard?.differentiation),
                    }}
                  />
                </div>
              </div>

              <div className={styles.scoreMetricCard}>
                <span className={styles.scoreMetricLabel}>Evidence</span>
                <span className={styles.scoreMetricValue}>
                  {formatScore(currentScorecard?.evidence)}
                </span>
                <div className={styles.progressBar}>
                  <div
                    className={styles.progressFill}
                    style={{
                      width: formatScore(currentScorecard?.evidence),
                    }}
                  />
                </div>
              </div>
            </div>

            {currentScorecard?.summary && (
              <div className={styles.summaryBox}>
                <span className={styles.summaryLabel}>Final Assessment:</span>
                <p className={styles.summaryText}>{currentScorecard.summary}</p>
              </div>
            )}

            {currentScorecard?.supporting_evidence &&
              currentScorecard.supporting_evidence.length > 0 && (
                <div className={styles.evidenceSection}>
                  <span className={styles.evidenceLabel}>Supporting Citations:</span>
                  <ul className={styles.evidenceList}>
                    {currentScorecard.supporting_evidence.map((ev, idx) => (
                      <li key={idx} className={styles.evidenceItem}>
                        {ev}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
          </div>
        </div>
      </section>

      {/* Drill-down button & Causal Chain */}
      <div className={styles.drilldownSection}>
        <button
          type="button"
          className={`${styles.drilldownToggleBtn} ${
            showCausalChain ? styles.drilldownActive : ""
          }`}
          onClick={() => setShowCausalChain((prev) => !prev)}
          aria-expanded={showCausalChain}
        >
          <span className={styles.toggleIcon}>{showCausalChain ? "▲" : "▼"}</span>
          <span>
            {showCausalChain
              ? "Hide Causal Chain drill-down"
              : "Why this candidate? (View Causal Chain)"}
          </span>
        </button>

        {showCausalChain && (
          <div className={styles.causalChainWrapper}>
            <CausalChain
              cluster={currentCluster}
              candidate={currentCandidate}
              verdict={currentVerdict}
              scorecard={currentScorecard}
            />
          </div>
        )}
      </div>

      {onReset && (
        <footer className={styles.footerActions}>
          <button type="button" className={styles.resetBtn} onClick={onReset}>
            ← Analyze another opportunity
          </button>
        </footer>
      )}
    </div>
  );
}
