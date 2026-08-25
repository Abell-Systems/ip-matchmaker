"""Cloud Run entrypoint: wraps the ADK agent graph in a FastAPI app.

Local dev: uvicorn main:app --reload --port 8080
Cloud Run: this module is the container's entrypoint (see Dockerfile).
"""

import asyncio
import json
import logging
import os
import uuid

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


app.router.routes = [r for r in app.router.routes if getattr(r, "path", None) != "/health"]


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "use_mock_bigquery": os.getenv("USE_MOCK_BIGQUERY", "true"),
        "gemini_api_key_configured": bool(os.getenv("GEMINI_API_KEY")),
        "model": os.getenv("GEMINI_MODEL", "gemini-3.5-flash"),
    }


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
    domain: str = Field(min_length=1)
    query: str = Field(default="solid electrolyte interphase")
    cluster_id: str | None = None


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

# ponytail: in-memory job store — valid because deploys pin --max-instances=1
# (see docs/deploy.md). Swap to Firestore only if multi-instance ever matters.
_jobs: dict[str, dict] = {}


async def _execute_analysis(job_id: str, req: AnalyzeRequest) -> dict:
    """Runs the agent graph for one cluster; returns candidates/verdicts/scorecards."""
    _jobs[job_id]["stage"] = "researching"
    _jobs[job_id]["progress"] = {}
    
    records = get_patents_datasource().search_patents(req.query, req.domain, max_results=20)
    demand_signals = get_demand_datasource().search_demand(req.query, req.domain)
    _jobs[job_id]["progress"]["patentsAnalyzed"] = len(records)
    
    _jobs[job_id]["stage"] = "clustering"
    clusters = cluster_patents(records, demand_signals)
    _jobs[job_id]["progress"]["clustersFound"] = len(clusters)
    _jobs[job_id]["clusters"] = [c.model_dump() for c in clusters]
    
    cluster_id = req.cluster_id or (clusters[0].cluster_id if clusters else "unknown")
    
    _jobs[job_id]["stage"] = "inventing"
    
    session = await _session_service.create_session(app_name="ip_matchmaker", user_id="web")
    prompt = (
        f"Mine the patent landscape for domain '{req.domain}' (query: '{req.query}'), "
        f"then propose, adversarially test, and score candidate inventions for cluster "
        f"'{cluster_id}'."
    )
    msg = types.Content(role="user", parts=[types.Part(text=prompt)])

    async def run() -> None:
        async for _ in _runner.run_async(user_id="web", session_id=session.id, new_message=msg):
            curr = await _session_service.get_session(
                app_name="ip_matchmaker", user_id="web", session_id=session.id
            )
            state = curr.state or {}
            
            cands = _as_list(state.get(CANDIDATE_INVENTIONS))
            if cands:
                _jobs[job_id]["progress"]["candidatesGenerated"] = len(cands)
                
            verdicts = _as_list(state.get(ADVERSARIAL_VERDICTS))
            if verdicts:
                _jobs[job_id]["stage"] = "adversarial"
                rej = 0
                surv = 0
                rev = 0
                for v in verdicts:
                    if isinstance(v, dict):
                        v_str = str(v.get("verdict", "")).lower()
                        if v_str == "rejected":
                            rej += 1
                        elif v_str == "survives":
                            surv += 1
                        elif v_str == "revised" or v_str == "revise":
                            rev += 1
                _jobs[job_id]["progress"]["candidatesRejected"] = rej
                _jobs[job_id]["progress"]["candidatesRevised"] = rev
                _jobs[job_id]["progress"]["candidatesSurvived"] = surv
                
            scores = _as_list(state.get(SCORED_CANDIDATES))
            if scores:
                _jobs[job_id]["stage"] = "governor"

    try:
        await run()
        final = await _session_service.get_session(
            app_name="ip_matchmaker", user_id="web", session_id=session.id
        )
        final_state = final.state or {}
        return {
            "candidates": _validated(InventionCandidate, final_state.get(CANDIDATE_INVENTIONS)),
            "verdicts": _validated(AdversarialVerdict, final_state.get(ADVERSARIAL_VERDICTS)),
            "scorecards": _validated(ScoreCard, final_state.get(SCORED_CANDIDATES)),
        }
    finally:
        await _session_service.delete_session(
            app_name="ip_matchmaker", user_id="web", session_id=session.id
        )


async def _run_job(job_id: str, req: AnalyzeRequest) -> None:
    async with _analyze_lock:
        try:
            result = await asyncio.wait_for(_execute_analysis(job_id, req), timeout=_ANALYZE_TIMEOUT_S)
            _jobs[job_id] = {"status": "done", "stage": "done", **result}
        except TimeoutError:
            _jobs[job_id] = {
                "status": "error",
                "stage": "error",
                "detail": f"Agent run exceeded {_ANALYZE_TIMEOUT_S}s.",
            }
        except Exception as exc:
            logger.exception("analyze job %s failed", job_id)
            _jobs[job_id] = {"status": "error", "stage": "error", "detail": str(exc)[:300]}


@app.post("/api/analyze", status_code=202)
async def analyze(req: AnalyzeRequest) -> dict:
    """Kicks off the full agent graph (research -> inventor/adversarial loop ->
    governor) in the background and returns a job id immediately. Poll
    GET /api/analyze/{job_id}; only one run may be in flight at a time."""
    if _analyze_lock.locked():
        raise HTTPException(status_code=503, detail="An analyze run is already in progress.")
    job_id = uuid.uuid4().hex
    _jobs[job_id] = {"status": "running", "stage": "queued"}
    asyncio.create_task(_run_job(job_id, req))
    return {"job_id": job_id, "status": "running", "stage": "queued"}


@app.get("/api/analyze/{job_id}")
async def analyze_status(job_id: str) -> dict:
    """Poll endpoint for a background analyze run."""
    job = _jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Unknown job id.")
    return job


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8080")))
