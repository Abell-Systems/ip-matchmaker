import { useEffect, useState } from "react";
import { getAnalyzeStatus, startAnalyze } from "./api/client";
import { ExecutionView } from "./components/UserZero/ExecutionView";
import { LandingView } from "./components/UserZero/LandingView";
import { ResultsView } from "./components/UserZero/ResultsView";
import type { JobStatusResponse } from "./types/patent";

type ViewState = "landing" | "executing" | "results" | "error";

export function App() {
  const [view, setView] = useState<ViewState>("landing");
  const [domain, setDomain] = useState<string>("");
  const [query, setQuery] = useState<string>("");
  const [jobId, setJobId] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<JobStatusResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [errorType, setErrorType] = useState<JobStatusResponse["error_type"] | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);

  const handleStartAnalysis = async (searchDomain: string, searchQuery: string) => {
    setIsLoading(true);
    setDomain(searchDomain);
    setQuery(searchQuery);
    setErrorMessage(null);
    setErrorType(null);

    try {
      const res = await startAnalyze(searchDomain, searchQuery);
      setJobId(res.job_id);
      setJobStatus({
        job_id: res.job_id,
        status: res.status as "running" | "done" | "error",
        stage: res.stage,
      });
      setView("executing");
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : "We couldn't start the analysis. Please try again.");
      setView("error");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (view !== "executing" || !jobId) return;
    let isMounted = true;

    const poll = async () => {
      try {
        const res = await getAnalyzeStatus(jobId);
        if (!isMounted) return;
        setJobStatus(res);

        if (res.status === "done") {
          setView("results");
        } else if (res.status === "error") {
          setErrorMessage(res.error || res.detail || "The analysis could not be completed.");
          setErrorType(res.error_type ?? null);
          setView("error");
        }
      } catch (err) {
        if (!isMounted) return;
        setErrorMessage(err instanceof Error ? err.message : "The analysis could not be completed.");
        setView("error");
      }
    };

    poll();
    const intervalId = setInterval(poll, 2000);
    return () => {
      isMounted = false;
      clearInterval(intervalId);
    };
  }, [view, jobId]);

  const handleReset = () => {
    setView("landing");
    setJobId(null);
    setJobStatus(null);
    setErrorMessage(null);
    setErrorType(null);
  };

  const handleRetry = () => {
    if (domain) void handleStartAnalysis(domain, query);
    else handleReset();
  };

  if (view === "executing") {
    return (
      <ExecutionView
        domain={domain}
        stage={jobStatus?.stage || "queued"}
        progress={jobStatus?.progress}
        events={jobStatus?.events}
        verdicts={jobStatus?.verdicts}
        candidates={jobStatus?.candidates}
      />
    );
  }

  if (view === "results" && jobStatus) {
    return <ResultsView domain={domain} result={jobStatus} onReset={handleReset} />;
  }

  if (view === "error") {
    const isQuotaExhausted = errorType === "quota_exhausted";
    const isPermissionError = errorMessage?.includes("PERMISSION_DENIED") || errorMessage?.includes("aiplatform.endpoints.predict");

    return (
      <main className="errorContainer">
        <header className="errorHeader">
          <div className="errorBrand">
            <span className="errorBrandMark">✦</span>
            <span>ABELL <strong>SYSTEMS</strong></span>
          </div>
          {domain && <div className="errorDomainBadge">{domain}</div>}
          <div className="errorEyebrow">ANALYSIS STATUS</div>
          <h1 className="errorTitle">
            {isQuotaExhausted ? "AI usage limit reached" : isPermissionError ? "AI agent needs access" : "We couldn't complete the analysis."}
          </h1>
          <p className="errorSubtitle">
            {isQuotaExhausted
              ? "Your research request is safe. The model quota is temporarily unavailable."
              : isPermissionError
                ? "The analysis engine is deployed, but its Cloud AI permission is not ready yet."
                : "Your opportunity wasn't lost. You can retry the analysis or start a new one."}
          </p>
        </header>

        <section className="errorCard" aria-label="Analysis status">
          <div className="errorStatusRow">
            <span className="errorStatusDot" />
            <span>{isPermissionError ? "Deployment configuration issue" : "Analysis interrupted"}</span>
          </div>
          <p className="errorMessage">
            {isPermissionError
              ? "The service account running Cloud Run cannot currently call the configured Gemini model through Vertex AI. The deployment configuration has been corrected; redeploying the service will apply it."
              : isQuotaExhausted
                ? "Please wait a moment and try again."
                : "The agent returned an unexpected error while processing this opportunity."}
          </p>
          {errorMessage && !isPermissionError && (
            <details className="errorTechnical">
              <summary>Technical details</summary>
              <code>{errorMessage}</code>
            </details>
          )}
        </section>

        <div className="errorActions">
          {!isQuotaExhausted && (
            <button type="button" className="errorPrimaryBtn" onClick={handleRetry}>Try again</button>
          )}
          <button type="button" className="errorSecondaryBtn" onClick={handleReset}>← Analyze another opportunity</button>
        </div>
      </main>
    );
  }

  return <LandingView onStartAnalysis={handleStartAnalysis} isLoading={isLoading} />;
}

export default App;
