"""Cloud Run entrypoint: wraps the ADK agent graph in a FastAPI app.

Local dev: uvicorn main:app --reload --port 8080
Cloud Run: this module is the container's entrypoint (see Dockerfile).
"""

import asyncio
import json
import logging
import os

from dotenv import load_dotenv

load_dotenv()

from fastapi import HTTPException, Query  # noqa: E402
from google.adk.cli.fast_api import get_fast_api_app  # noqa: E402
from google.adk.runners import Runner  # noqa: E402
from google.adk.sessions import InMemorySessionService  # noqa: E402
from google.genai import types  # noqa: E402
from pydantic import BaseModel, Field, ValidationError  # noqa: E402

from patent_agent.agent import root_agent  # noqa: E402
from patent_agent.shared.state_keys import (  # noqa: E402
    ADVERSARIAL_VERDICTS,
    CANDIDATE_INVENTIONS,
    SCORED_CANDIDATES,
)
from patent_agent.tools.bigquery_patents import get_patents_datasource  # noqa: E402
from patent_agent.tools.clustering import cluster_patents  # noqa: E402
from patent_agent.tools.demand_sources import get_demand_datasource  # noqa: E402
from patent_agent.tools.schemas import (  # noqa: E402
    AdversarialVerdict,
    InventionCandidate,
    PatentRecord,
    ScoreCard,
)

logger = logging.getLogger(__name__)

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
def get_landscape(
    query: str = Query(min_length=1),
    domain: str = Query(min_length=1),
    max_results: int = Query(20, ge=1, le=100),
) -> dict:
    """Deterministic, LLM-free view of the research + clustering pipeline.

    Calls the same tools research_agent uses, without going through the ADK
    Runner/Gemini — lets the "heavy lifting of massive datasets" part of the
    pipeline be demoed and deployed before a Gemini API key is wired in.
    """
    records = get_patents_datasource().search_patents(query, domain, max_results)
    demand_signals = get_demand_datasource().search_demand(query, domain)
    clusters = cluster_patents(records, demand_signals)
    return {
        "query": query,
        "domain": domain,
        "patents": [r.model_dump() for r in records],
        "clusters": [c.model_dump() for c in clusters],
    }


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


def _validated(model_cls, items) -> list[dict]:
    """Keep only entries that match the shared schema; drop the rest.

    Agents occasionally emit free text or partial JSON; passing that through
    verbatim crashes the frontend, which dereferences typed fields.
    """
    out: list[dict] = []
    for item in _as_list(items):
        try:
            out.append(model_cls.model_validate(item).model_dump())
        except ValidationError:
            logger.warning("dropping malformed %s entry: %.120r", model_cls.__name__, item)
    return out


# One full-graph run at a time: it burns minutes of free-tier Gemini quota and
# concurrent runs would serialize unpredictably on the RateLimiter plugin.
_analyze_lock = asyncio.Lock()
_ANALYZE_TIMEOUT_S = int(os.getenv("ANALYZE_TIMEOUT_SECONDS", "900"))


@app.post("/api/analyze")
async def analyze(req: AnalyzeRequest) -> dict:
    """Runs the full agent graph (research -> inventor/adversarial loop ->
    governor) for one cluster and returns its candidates, verdicts, and
    scorecards. Rate-limited to the free-tier quota via RateLimiter — do not
    call this endpoint in a tight loop from the frontend or tests."""
    if _analyze_lock.locked():
        raise HTTPException(status_code=503, detail="An analyze run is already in progress.")
    async with _analyze_lock:
        session = await _session_service.create_session(app_name="ip_matchmaker", user_id="web")
        prompt = (
            f"Mine the patent landscape for domain '{req.domain}' (query: '{req.query}'), "
            f"then propose, adversarially test, and score candidate inventions for cluster "
            f"'{req.cluster_id}'."
        )
        msg = types.Content(role="user", parts=[types.Part(text=prompt)])

        async def run() -> None:
            async for _ in _runner.run_async(user_id="web", session_id=session.id, new_message=msg):
                pass

        try:
            try:
                await asyncio.wait_for(run(), timeout=_ANALYZE_TIMEOUT_S)
            except TimeoutError:
                raise HTTPException(
                    status_code=504,
                    detail=f"Agent run exceeded {_ANALYZE_TIMEOUT_S}s.",
                ) from None
            final = await _session_service.get_session(
                app_name="ip_matchmaker", user_id="web", session_id=session.id
            )
            state = final.state or {}
            return {
                "candidates": _validated(InventionCandidate, state.get(CANDIDATE_INVENTIONS)),
                "verdicts": _validated(AdversarialVerdict, state.get(ADVERSARIAL_VERDICTS)),
                "scorecards": _validated(ScoreCard, state.get(SCORED_CANDIDATES)),
            }
        finally:
            await _session_service.delete_session(
                app_name="ip_matchmaker", user_id="web", session_id=session.id
            )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8080")))
