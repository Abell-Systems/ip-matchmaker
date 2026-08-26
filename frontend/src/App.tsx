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
      setErrorMessage(
        err instanceof Error
          ? err.message
          : "We couldn't complete the analysis. Your opportunity wasn't lost. Try again."
      );
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
          setErrorMessage(
            res.error ||
              res.detail ||
              "We couldn't complete the analysis. Your opportunity wasn't lost. Try again."
          );
          setErrorType(res.error_type ?? null);
          setView("error");
        }
      } catch (err) {
        if (!isMounted) return;
        setErrorMessage(
          err instanceof Error
            ? err.message
            : "We couldn't complete the analysis. Your opportunity wasn't lost. Try again."
        );
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
    if (domain) {
      void handleStartAnalysis(domain, query);
    } else {
      handleReset();
    }
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
    return (
      <ResultsView
        domain={domain}
        result={jobStatus}
        onReset={handleReset}
      />
    );
  }

  if (view === "error") {
    const isQuotaExhausted = errorType === "quota_exhausted";
    return (
      <main className="errorContainer">
        <header className="errorHeader">
          {domain && <div className="errorDomainBadge">{domain}</div>}
          <h1 className="errorTitle">
            {isQuotaExhausted ? "AI usage limit reached" : "We couldn't complete the analysis."}
          </h1>
          <p className="errorSubtitle">
            {isQuotaExhausted
              ? "Your research has not been lost. Please try again later."
              : "Your opportunity wasn't lost. Try again."}
          </p>
        </header>

        {errorMessage && (
          <div className="errorCard">
            <div className="errorStatusRow">
              <span className="errorIcon">⚠</span>
              <span className="errorLabel">Reason</span>
            </div>
            <p className="errorMessage">{errorMessage}</p>
          </div>
        )}

        <div className="errorActions">
          {!isQuotaExhausted && (
            <button type="button" className="errorPrimaryBtn" onClick={handleRetry}>
              Try again
            </button>
          )}
          <button type="button" className="errorSecondaryBtn" onClick={handleReset}>
            ← Analyze another opportunity
          </button>
        </div>
      </main>
    );
  }

  return (
    <LandingView
      onStartAnalysis={handleStartAnalysis}
      isLoading={isLoading}
    />
  );
}

export default App;

