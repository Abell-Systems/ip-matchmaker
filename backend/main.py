"""Cloud Run entrypoint: wraps the ADK agent graph in a FastAPI app.

Local dev: uvicorn main:app --reload --port 8080
Cloud Run: this module is the container's entrypoint (see Dockerfile).
"""

import json
import os

from dotenv import load_dotenv

load_dotenv()

from google.adk.cli.fast_api import get_fast_api_app  # noqa: E402
from google.adk.runners import Runner  # noqa: E402
from google.adk.sessions import InMemorySessionService  # noqa: E402
from google.genai import types  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402

from patent_agent.agent import root_agent  # noqa: E402
from patent_agent.shared.state_keys import (  # noqa: E402
    ADVERSARIAL_VERDICTS,
    CANDIDATE_INVENTIONS,
    SCORED_CANDIDATES,
)
from patent_agent.tools import cluster_patents_tool, search_patents_tool  # noqa: E402

# reuse the free-tier pacing plugin; do not add a second rate limiter anywhere
from run_pipeline import RateLimiter  # noqa: E402

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


_session_service = InMemorySessionService()
_runner = Runner(
    agent=root_agent,
    app_name="ip_matchmaker",
    session_service=_session_service,
    plugins=[RateLimiter()],
)


class AnalyzeRequest(BaseModel):
    query: str = Field(min_length=1)
    domain: str = Field(min_length=1)
    cluster_id: str = Field(min_length=1)


def _as_list(value) -> list:
    """Normalize one state entry to a JSON-friendly list.

    Structured-output agents store a dict (or its JSON string); the inventor
    emits a single candidate; the adversarial agent still emits free text.
    """
    if value is None:
        return []
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            return [value]
    if isinstance(value, dict):
        for key in ("candidate", "scorecards"):
            if key in value:
                return _as_list(value[key])
        return [value]
    return list(value)


@app.post("/api/analyze")
async def analyze(req: AnalyzeRequest) -> dict:
    """Runs the full agent graph (research -> inventor/adversarial loop ->
    governor) for one cluster and returns its candidates, verdicts, and
    scorecards. Rate-limited to the free-tier quota via RateLimiter — do not
    call this endpoint in a tight loop from the frontend or tests."""
    session = await _session_service.create_session(app_name="ip_matchmaker", user_id="web")
    prompt = (
        f"Mine the patent landscape for domain '{req.domain}' (query: '{req.query}'), "
        f"then propose, adversarially test, and score candidate inventions for cluster "
        f"'{req.cluster_id}'."
    )
    msg = types.Content(role="user", parts=[types.Part(text=prompt)])
    for _ in _runner.run(user_id="web", session_id=session.id, new_message=msg):
        pass
    final = await _session_service.get_session(
        app_name="ip_matchmaker", user_id="web", session_id=session.id
    )
    state = final.state or {}
    return {
        "candidates": _as_list(state.get(CANDIDATE_INVENTIONS)),
        "verdicts": _as_list(state.get(ADVERSARIAL_VERDICTS)),
        "scorecards": _as_list(state.get(SCORED_CANDIDATES)),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8080")))
