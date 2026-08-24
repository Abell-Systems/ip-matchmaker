// Thin fetch wrapper for the backend. getLandscape hits the deterministic
// /api/landscape endpoint (research + clustering, no Gemini call); analyzeCluster
// runs the full Gemini-backed agent graph via POST /api/analyze.

import type {
  AdversarialVerdict,
  InventionCandidate,
  PatentCluster,
  PatentRecord,
  ScoreCard,
} from "../types/patent";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8080";

async function requestJson(url: string, init?: RequestInit): Promise<unknown> {
  const response = await fetch(url, init);
  if (!response.ok) {
    const body = await response.text().catch(() => "");
    throw new Error(`Request failed (${response.status}): ${body.slice(0, 300)}`);
  }
  return response.json();
}

export interface LandscapeResponse {
  query: string;
  domain: string;
  patents: PatentRecord[];
  clusters: PatentCluster[];
}

export async function getLandscape(
  query: string,
  domain: string,
  maxResults = 20,
  signal?: AbortSignal,
): Promise<LandscapeResponse> {
  const params = new URLSearchParams({ query, domain, max_results: String(maxResults) });
  return (await requestJson(`${API_BASE_URL}/api/landscape?${params}`, { signal })) as LandscapeResponse;
}

export interface AnalyzeResult {
  candidates: InventionCandidate[];
  verdicts: AdversarialVerdict[];
  scorecards: ScoreCard[];
}

export type AnalyzeStatus =
  | { status: "running" }
  | ({ status: "done" } & AnalyzeResult)
  | { status: "error"; detail: string };

// POST kicks off the agent graph in the background and returns a job id;
// poll getAnalyzeStatus until status is "done" or "error".
export async function startAnalyze(
  query: string,
  domain: string,
  clusterId: string,
  signal?: AbortSignal,
): Promise<{ job_id: string }> {
  return (await requestJson(`${API_BASE_URL}/api/analyze`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ query, domain, cluster_id: clusterId }),
    signal,
  })) as { job_id: string };
}

export async function getAnalyzeStatus(jobId: string, signal?: AbortSignal): Promise<AnalyzeStatus> {
  return (await requestJson(`${API_BASE_URL}/api/analyze/${jobId}`, { signal })) as AnalyzeStatus;
}
