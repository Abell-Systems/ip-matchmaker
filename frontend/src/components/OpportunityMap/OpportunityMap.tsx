import { useEffect, useState } from "react";
import { analyzeCluster, getLandscape } from "../../api/client";
import type { AnalyzeResponse } from "../../api/client";
import type { PatentCluster, PatentRecord } from "../../types/patent";
import styles from "./OpportunityMap.module.css";

// Patent landscape view (/api/landscape): user-editable query/domain search,
// clusters expandable to their representative patents. Expanded cards can run
// the full Gemini-backed agent graph (inventor/adversarial/governor) via
// POST /api/analyze and show scored, citation-backed candidates.

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
  const [analysis, setAnalysis] = useState<Record<string, AnalyzeResponse | "loading" | "error">>(
    {},
  );

  useEffect(() => {
    const controller = new AbortController();
    setClusters(null);
    setError(null);
    setExpandedClusterId(null);
    setAnalysis({});
    getLandscape(search.query, search.domain, 20, controller.signal)
      .then((data) => {
        setClusters(data.clusters);
        setPatents(data.patents);
      })
      .catch((err: unknown) => {
        if (controller.signal.aborted) return;
        setError(err instanceof Error ? err.message : String(err));
      });
    return () => controller.abort();
  }, [search]);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSearch({ query: queryInput, domain: domainInput });
  }

  function patentByNumber(publicationNumber: string): PatentRecord | undefined {
    return patents.find((p) => p.publication_number === publicationNumber);
  }

  function handleAnalyze(clusterId: string) {
    if (analysis[clusterId] === "loading") return;
    setAnalysis((prev) => ({ ...prev, [clusterId]: "loading" }));
    analyzeCluster(search.query, search.domain, clusterId)
      .then((data) => setAnalysis((prev) => ({ ...prev, [clusterId]: data })))
      .catch(() => setAnalysis((prev) => ({ ...prev, [clusterId]: "error" })));
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
        <div className={styles.placeholder} role="status" aria-live="polite">
          <p>Could not load landscape from the backend: {error}</p>
          <p>Is the backend running? See README.md for spin-up instructions.</p>
        </div>
      )}

      {!error && !clusters && (
        <div className={styles.placeholder} role="status" aria-live="polite">
          Loading patent landscape…
        </div>
      )}

      {!error && clusters && (
        <>
          <p className={styles.subtitle}>
            Domain: <strong>{search.domain}</strong> — query: <strong>{search.query}</strong>
          </p>
          <div className={styles.grid}>
            {clusters.map((cluster) => {
              const expanded = expandedClusterId === cluster.cluster_id;
              const clusterAnalysis = analysis[cluster.cluster_id];
              return (
                <article key={cluster.cluster_id} className={styles.card}>
                  <button
                    type="button"
                    className={styles.cardToggle}
                    onClick={() => setExpandedClusterId(expanded ? null : cluster.cluster_id)}
                    aria-expanded={expanded}
                  >
                    <header className={styles.cardHeader}>
                      <h2>{cluster.label}</h2>
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
                    <>
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
                      <button
                        type="button"
                        className={styles.analyzeButton}
                        onClick={() => handleAnalyze(cluster.cluster_id)}
                        disabled={clusterAnalysis === "loading"}
                      >
                        Propose &amp; score inventions for this cluster
                      </button>
                      {clusterAnalysis === "loading" && (
                        <p className={styles.patentMeta} role="status" aria-live="polite">
                          Running inventor/adversarial/governor agents… (this takes a couple of
                          minutes)
                        </p>
                      )}
                      {clusterAnalysis === "error" && (
                        <p className={styles.patentMeta} role="status" aria-live="polite">
                          Analysis failed — check backend logs.
                        </p>
                      )}
                      {clusterAnalysis && clusterAnalysis !== "loading" && clusterAnalysis !== "error" && (
                        <ul className={styles.patentList}>
                          {clusterAnalysis.scorecards.map((card) => {
                            const candidate = clusterAnalysis.candidates.find(
                              (c) => c.candidate_id === card.candidate_id,
                            );
                                return (
                                  <li key={card.candidate_id}>
                                    <strong>{candidate?.title ?? card.candidate_id}</strong>
                                    <p>{card.summary}</p>
                                    <p className={styles.patentMeta}>
                                      novelty {card.novelty} · prior-art risk {card.prior_art_risk}{" "}
                                      · differentiation {card.differentiation} · evidence{" "}
                                      {card.evidence}
                                    </p>
                                    <p className={styles.patentMeta}>
                                      cited: {card.supporting_evidence.join(", ")}
                                    </p>
                                  </li>
                                );
                              },
                            )}
                          </ul>
                        )}
                     </>
                  )}
                </article>
              );
            })}
          </div>
          <p className={styles.footnote}>
            Adversarial verdicts are shown in the backend run log; the cards above show each
            surviving candidate with its governor scores and cited prior art.
          </p>
        </>
      )}
    </div>
  );
}
