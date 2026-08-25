import { useState } from "react";
import styles from "./LandingView.module.css";

interface LandingViewProps {
  onStartAnalysis: (domain: string, query: string) => void;
  isLoading?: boolean;
}

export function LandingView({ onStartAnalysis, isLoading }: LandingViewProps) {
  const [domain, setDomain] = useState("Solid-state electrolytes for EV batteries");
  const [query, setQuery] = useState("solid electrolyte interphase");

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (domain.trim()) {
      onStartAnalysis(domain.trim(), query.trim());
    }
  }

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <h1 className={styles.title}>
          Find invention opportunities hidden in the patent landscape.
        </h1>
        <p className={styles.subtitle}>
          Give the agent a technology area. It researches prior art, finds white-space, invents candidates and attacks them before scoring the survivors.
        </p>
      </header>

      <form className={styles.form} onSubmit={handleSubmit}>
        <div className={styles.fieldGroup}>
          <label htmlFor="domainInput">Domain</label>
          <input
            id="domainInput"
            type="text"
            className={styles.input}
            value={domain}
            onChange={(e) => setDomain(e.target.value)}
            placeholder="e.g. Solid-state electrolytes for EV batteries"
            required
          />
        </div>

        <div className={styles.fieldGroup}>
          <label htmlFor="queryInput">
            Research query <span className={styles.optional}>(optional)</span>
          </label>
          <input
            id="queryInput"
            type="text"
            className={styles.input}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="e.g. solid electrolyte interphase"
          />
        </div>

        <button type="submit" className={styles.submitBtn} disabled={isLoading}>
          {isLoading ? "Starting analysis…" : "Analyze opportunity"}
        </button>
      </form>
    </div>
  );
}
