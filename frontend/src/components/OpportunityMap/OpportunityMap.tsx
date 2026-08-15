import { useEffect, useState } from "react";
import { getLandscape } from "../../api/client";
import type { PatentCluster } from "../../types/patent";
import styles from "./OpportunityMap.module.css";

// Real-but-minimal view of the LLM-free research+clustering pipeline
// (/api/landscape). The full Invention Opportunity Map — candidate
// inventions, scores, "explain" drill-down — lands Days 12-13 once the
// Gemini-backed agents (inventor/adversarial/governor) have a real API key.
// This is intentionally simple: proof that real data flows end to end.

const DOMAIN = "solid-state battery electrolytes";
const DEFAULT_QUERY = "solid electrolyte interphase";

export function OpportunityMap() {
  const [clusters, setClusters] = useState<PatentCluster[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getLandscape(DEFAULT_QUERY, DOMAIN, 20)
      .then((data) => setClusters(data.clusters))
      .catch((err: unknown) => setError(err instanceof Error ? err.message : String(err)));
  }, []);

  if (error) {
    return (
      <div className={styles.placeholder}>
        <p>Could not load landscape from the backend: {error}</p>
        <p>Is the backend running? See README.md for spin-up instructions.</p>
      </div>
    );
  }

  if (!clusters) {
    return <div className={styles.placeholder}>Loading patent landscape…</div>;
  }

  return (
    <div>
      <p className={styles.subtitle}>
        Domain: <strong>{DOMAIN}</strong> — query: <strong>{DEFAULT_QUERY}</strong>
      </p>
      <div className={styles.grid}>
        {clusters.map((cluster) => (
          <article key={cluster.cluster_id} className={styles.card}>
            <header className={styles.cardHeader}>
              <h3>{cluster.label}</h3>
              {cluster.is_white_space && <span className={styles.badge}>white space</span>}
            </header>
            <dl className={styles.stats}>
              <dt>Patents</dt>
              <dd>{cluster.patent_count}</dd>
              <dt>White-space score</dt>
              <dd>{cluster.white_space_score.toFixed(2)}</dd>
            </dl>
            <p className={styles.representative}>
              Representative: {cluster.representative_patents.join(", ")}
            </p>
          </article>
        ))}
      </div>
      <p className={styles.footnote}>
        Candidate inventions, adversarial verdicts and governor scores appear here once the
        Gemini-backed agents are wired to a real API key (see docs/roadmap.md).
      </p>
    </div>
  );
}
