import { useEffect, useState } from "react";
import { getLandscape } from "../../api/client";
import type { PatentCluster, PatentRecord } from "../../types/patent";
import styles from "./OpportunityMap.module.css";

// Real-but-minimal view of the LLM-free research+clustering pipeline
// (/api/landscape). The full Invention Opportunity Map — candidate
// inventions, scores, "explain" drill-down — lands Days 12-13 once the
// Gemini-backed agents (inventor/adversarial/governor) have a real API key.
// Query/domain are user-editable and clusters expand to their representative
// patents; still entirely backed by mock data, no LLM calls involved.

const DEFAULT_DOMAIN = "solid-state battery electrolytes";
const DEFAULT_QUERY = "solid electrolyte interphase";

export function OpportunityMap() {
  const [queryInput, setQueryInput] = useState(DEFAULT_QUERY);
  const [domainInput, setDomainInput] = useState(DEFAULT_DOMAIN);
  const [search, setSearch] = useState({ query: DEFAULT_QUERY, domain: DEFAULT_DOMAIN });
  const [clusters, setClusters] = useState<PatentCluster[] | null>(null);
  const [patents, setPatents] = useState<PatentRecord[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [expandedClusterId, setExpandedClusterId] = useState<string | null>(null);

  useEffect(() => {
    setClusters(null);
    setError(null);
    setExpandedClusterId(null);
    getLandscape(search.query, search.domain, 20)
      .then((data) => {
        setClusters(data.clusters);
        setPatents(data.patents);
      })
      .catch((err: unknown) => setError(err instanceof Error ? err.message : String(err)));
  }, [search]);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSearch({ query: queryInput, domain: domainInput });
  }

  function patentByNumber(publicationNumber: string): PatentRecord | undefined {
    return patents.find((p) => p.publication_number === publicationNumber);
  }

  return (
    <div>
      <form className={styles.searchForm} onSubmit={handleSubmit}>
        <label>
          Query
          <input value={queryInput} onChange={(e) => setQueryInput(e.target.value)} />
        </label>
        <label>
          Domain
          <input value={domainInput} onChange={(e) => setDomainInput(e.target.value)} />
        </label>
        <button type="submit">Search</button>
      </form>

      {error && (
        <div className={styles.placeholder}>
          <p>Could not load landscape from the backend: {error}</p>
          <p>Is the backend running? See README.md for spin-up instructions.</p>
        </div>
      )}

      {!error && !clusters && <div className={styles.placeholder}>Loading patent landscape…</div>}

      {!error && clusters && (
        <>
          <p className={styles.subtitle}>
            Domain: <strong>{search.domain}</strong> — query: <strong>{search.query}</strong>
          </p>
          <div className={styles.grid}>
            {clusters.map((cluster) => {
              const expanded = expandedClusterId === cluster.cluster_id;
              return (
                <article key={cluster.cluster_id} className={styles.card}>
                  <button
                    type="button"
                    className={styles.cardToggle}
                    onClick={() => setExpandedClusterId(expanded ? null : cluster.cluster_id)}
                    aria-expanded={expanded}
                  >
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
                      {" "}({expanded ? "hide" : "show"} details)
                    </p>
                  </button>
                  {expanded && (
                    <ul className={styles.patentList}>
                      {cluster.representative_patents.map((pubNumber) => {
                        const patent = patentByNumber(pubNumber);
                        if (!patent) return <li key={pubNumber}>{pubNumber}</li>;
                        return (
                          <li key={pubNumber}>
                            <strong>{patent.title}</strong>
                            <p>{patent.abstract}</p>
                            <p className={styles.patentMeta}>
                              {patent.assignee.join(", ")} · {patent.publication_date} ·{" "}
                              {patent.citation_count} citations
                            </p>
                          </li>
                        );
                      })}
                    </ul>
                  )}
                </article>
              );
            })}
          </div>
          <p className={styles.footnote}>
            Candidate inventions, adversarial verdicts and governor scores appear here once the
            Gemini-backed agents are wired to a real API key (see docs/roadmap.md).
          </p>
        </>
      )}
    </div>
  );
}
