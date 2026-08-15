// Thin fetch wrapper for the backend. getLandscape hits the LLM-free
// /api/landscape endpoint (research + clustering only, no Gemini call needed),
// which is real and working. Endpoints for the Gemini-backed agents
// (inventor/adversarial/governor) land once GEMINI_API_KEY is wired in — see
// docs/roadmap.md.

import type { PatentCluster, PatentRecord } from "../types/patent";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8080";

export async function getHealth(): Promise<{ status: string }> {
  const response = await fetch(`${API_BASE_URL}/health`);
  if (!response.ok) {
    throw new Error(`Health check failed: ${response.status}`);
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
): Promise<LandscapeResponse> {
  const params = new URLSearchParams({ query, domain, max_results: String(maxResults) });
  const response = await fetch(`${API_BASE_URL}/api/landscape?${params}`);
  if (!response.ok) {
    throw new Error(`Landscape request failed: ${response.status}`);
  }
  return response.json();
}
