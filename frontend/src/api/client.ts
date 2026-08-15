// Thin fetch wrapper for the backend's ADK-served agent endpoints.
// Not wired to real calls yet — endpoints are frozen and consumed starting Day 12
// (see docs/roadmap.md). Kept minimal so the contract is obvious once agent
// endpoints exist.

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8080";

export async function getHealth(): Promise<{ status: string }> {
  const response = await fetch(`${API_BASE_URL}/health`);
  if (!response.ok) {
    throw new Error(`Health check failed: ${response.status}`);
  }
  return response.json();
}
