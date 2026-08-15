"""Cloud Run entrypoint: wraps the ADK agent graph in a FastAPI app.

Local dev: uvicorn main:app --reload --port 8080
Cloud Run: this module is the container's entrypoint (see Dockerfile).
"""

import os

from dotenv import load_dotenv

load_dotenv()

from google.adk.cli.fast_api import get_fast_api_app  # noqa: E402

from patent_agent.tools import cluster_patents_tool, search_patents_tool  # noqa: E402

AGENTS_DIR = os.path.dirname(os.path.abspath(__file__))

# ADK's own origin-check middleware rejects cross-origin requests unless the
# origin is listed here (a plain CORSMiddleware added after the fact does not
# override it). Comma-separated via FRONTEND_ORIGINS so Cloud Run deploys can
# set the real frontend origin without a code change.
_ALLOWED_ORIGINS = os.getenv("FRONTEND_ORIGINS", "http://localhost:5173").split(",")

app = get_fast_api_app(
    agents_dir=AGENTS_DIR,
    web=False,
    allow_origins=_ALLOWED_ORIGINS,
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/landscape")
def get_landscape(query: str, domain: str, max_results: int = 20) -> dict:
    """Deterministic, LLM-free view of the research + clustering pipeline.

    Calls the same tools research_agent uses, without going through the ADK
    Runner/Gemini — lets the "heavy lifting of massive datasets" part of the
    pipeline be demoed and deployed before a Gemini API key is wired in.
    """
    patents = search_patents_tool(query, domain, max_results)
    clusters = cluster_patents_tool(query, domain, max_results)
    return {"query": query, "domain": domain, "patents": patents, "clusters": clusters}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8080")))
