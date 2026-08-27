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

from datetime import datetime, timezone

from fastapi import HTTPException, Query  # noqa: E402
from google.adk.agents import LoopAgent, SequentialAgent  # noqa: E402
from google.adk.cli.fast_api import get_fast_api_app  # noqa: E402
from google.adk.runners import Runner  # noqa: E402
from google.adk.sessions import InMemorySessionService  # noqa: E402
from google.genai import types  # noqa: E402
from pydantic import BaseModel, Field, ValidationError  # noqa: E402

from patent_agent.config import INVENTION_LOOP_MAX_ITERATIONS  # noqa: E402
from patent_agent.shared.state_keys import (  # noqa: E402
    ADVERSARIAL_VERDICTS,
    CANDIDATE_INVENTIONS,
    SCORED_CANDIDATES,
    SELECTED_CLUSTER_CONTEXT,
)
from patent_agent.sub_agents.adversarial.agent import build_adversarial_agent  # noqa: E402
from patent_agent.sub_agents.governor.agent import build_governor_agent  # noqa: E402
from patent_agent.sub_agents.inventor.agent import build_inventor_agent  # noqa: E402
from patent_agent.tools.bigquery_patents import get_patents_datasource  # noqa: E402
from patent_agent.tools.clustering import cluster_patents, patents_for_demand_signal  # noqa: E402
from patent_agent.tools.context import build_cluster_context  # noqa: E402
from patent_agent.tools.demand_sources import get_demand_datasource  # noqa: E402
from patent_agent.tools.schemas import (  # noqa: E402
    AdversarialVerdict,
    AgentEventItem,
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


from patent_agent.provider import LLMProvider  # noqa: E402


@app.get("/health")
def health() -> dict:
    try:
        provider_status = LLMProvider.get_status()
    except Exception as err:
        provider_status = {
            "model_provider": os.getenv("MODEL_PROVIDER", "unknown"),
            "model": "error",
            "error": str(err),
        }
    return {
        "status": "ok",
        "use_mock_bigquery": os.getenv("USE_MOCK_BIGQUERY", "true"),
        **provider_status,
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


@app.get("/api/demand/{signal_id}/patents")
def get_patents_for_demand(
    signal_id: str,
    query: str = Query(min_length=1),
    domain: str = Query(min_length=1),
    max_results: int = Query(20, ge=1, le=100),
) -> dict:
    """Patents related to one demand signal (e.g. an Innoget technology call).

    `query`/`domain` re-run the same demand search the signal_id came from
    (demand signals aren't stored server-side, only returned from /api/landscape),
    so this must be called with the same args used to find that signal_id.
    """
    demand_signals = get_demand_datasource().search_demand(query, domain)
    signal = next((s for s in demand_signals if s.id == signal_id), None)
    if signal is None:
        raise HTTPException(status_code=404, detail=f"Demand signal '{signal_id}' not found for that query/domain")
    records = patents_for_demand_signal(signal, domain, max_results)
    return {
        "demand_signal": signal.model_dump(),
        "patents": [r.model_dump() for r in records],
    }


# /api/analyze pre-mines patents/clusters deterministically in Python (see
# _execute_analysis below) before ever touching the LLM, so this pipeline skips
# research_agent entirely — asking it to re-mine via tool calls was pure
# duplicate work and the single biggest source of prompt bloat (its own
# multi-tool-call turn could exceed free-tier TPM caps on its own, regardless
# of the include_contents fix on the agents below). The interactive `adk web`
# graph (patent_agent/agent.py's root_agent) still includes research_agent —
# it has no pre-mined data to seed from.
_invention_loop = LoopAgent(
    name="invention_loop",
    sub_agents=[build_inventor_agent(), build_adversarial_agent()],
    max_iterations=INVENTION_LOOP_MAX_ITERATIONS,
)
_analyze_pipeline = SequentialAgent(
    name="patent_innovation_agent_api",
    sub_agents=[_invention_loop, build_governor_agent()],
)

_session_service = InMemorySessionService()
_runner = Runner(
    agent=_analyze_pipeline,
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


def _emit_event(
    job_id: str,
    event_type: str,
    message: str,
    candidate_id: str | None = None,
    evidence: dict | list | str | None = None,
) -> None:
    if "events" not in _jobs.get(job_id, {}):
        if job_id in _jobs:
            _jobs[job_id]["events"] = []
        else:
            return
    ts = datetime.now(timezone.utc).isoformat()
    evt = {
        "type": event_type,
        "timestamp": ts,
        "message": message,
    }
    if candidate_id:
        evt["candidateId"] = candidate_id
    if evidence is not None:
        evt["evidence"] = evidence
    _jobs[job_id]["events"].append(evt)


def reconcile_candidate_verdicts(
    verdicts: list[dict], scorecards: list[dict]
) -> list[dict]:
    """Ensures backend produces authoritative verdict: if governor scorecard finds
    direct anticipation or blocking prior art, force verdict to 'rejected'."""
    reconciled = []
    for v in verdicts:
        v_copy = dict(v)
        cand_id = v_copy.get("candidate_id")
        sc = next((s for s in scorecards if isinstance(s, dict) and s.get("candidate_id") == cand_id), None)
        if sc:
            summary = (sc.get("summary") or "").lower()
            if (
                "directly anticipated" in summary
                or "no room for novelty" in summary
                or "cannot be recommended" in summary
            ):
                v_copy["verdict"] = "rejected"
        reconciled.append(v_copy)
    return reconciled


async def _execute_analysis(job_id: str, req: AnalyzeRequest) -> dict:
    """Runs the agent graph for one cluster; returns candidates/verdicts/scorecards."""
    _jobs[job_id]["stage"] = "researching"
    _jobs[job_id]["progress"] = {}
    _jobs[job_id]["events"] = []
    
    records = get_patents_datasource().search_patents(req.query, req.domain, max_results=20)
    demand_signals = get_demand_datasource().search_demand(req.query, req.domain)
    _jobs[job_id]["progress"]["patentsAnalyzed"] = len(records)
    _emit_event(
        job_id,
        "research_completed",
        f"Researched {len(records)} patents",
        evidence={"patentsAnalyzed": len(records)},
    )
    
    _jobs[job_id]["stage"] = "clustering"
    clusters = cluster_patents(records, demand_signals)
    _jobs[job_id]["progress"]["clustersFound"] = len(clusters)
    _jobs[job_id]["clusters"] = [c.model_dump() for c in clusters]
    _emit_event(
        job_id,
        "landscape_clustered",
        f"Found {len(clusters)} white-space opportunities",
        evidence={"clustersFound": len(clusters)},
    )
    
    cluster_id = req.cluster_id or (clusters[0].cluster_id if clusters else "unknown")
    selected_cluster = next((c for c in clusters if c.cluster_id == cluster_id), None)
    cluster_context = (
        build_cluster_context(selected_cluster, records, demand_signals) if selected_cluster else ""
    )

    _jobs[job_id]["stage"] = "inventing"

    session = await _session_service.create_session(
        app_name="ip_matchmaker",
        user_id="web",
        state={SELECTED_CLUSTER_CONTEXT: cluster_context},
    )
    prompt = (
        f"Propose, adversarially test, and score a candidate invention for cluster "
        f"'{cluster_id}' in domain '{req.domain}', using the selected cluster context provided."
    )
    msg = types.Content(role="user", parts=[types.Part(text=prompt)])

    seen_candidates: set[str] = set()
    seen_verdict_indices: set[int] = set()
    seen_assessment = False

    async def run() -> None:
        nonlocal seen_assessment
        async for _ in _runner.run_async(user_id="web", session_id=session.id, new_message=msg):
            curr = await _session_service.get_session(
                app_name="ip_matchmaker", user_id="web", session_id=session.id
            )
            state = curr.state or {}
            
            cands = _as_list(state.get(CANDIDATE_INVENTIONS))
            if cands:
                _jobs[job_id]["progress"]["candidatesGenerated"] = len(cands)
                for cand in cands:
                    cand_id = "unknown"
                    cand_title = ""
                    if isinstance(cand, dict):
                        cand_id = str(cand.get("candidate_id", "unknown"))
                        cand_title = cand.get("title", "")
                    elif hasattr(cand, "candidate_id"):
                        cand_id = str(getattr(cand, "candidate_id"))
                        cand_title = getattr(cand, "title", "")
                    else:
                        cand_id = str(cand)

                    if cand_id not in seen_candidates:
                        seen_candidates.add(cand_id)
                        _emit_event(
                            job_id,
                            "candidate_generated",
                            f"Generated Candidate #{cand_id}" + (f": {cand_title}" if cand_title else ""),
                            candidate_id=cand_id,
                            evidence=cand if isinstance(cand, (dict, list, str, int, float)) else str(cand),
                        )
                
            verdicts = _as_list(state.get(ADVERSARIAL_VERDICTS))
            if verdicts:
                _jobs[job_id]["stage"] = "adversarial"
                rej = 0
                surv = 0
                rev = 0
                for idx, v in enumerate(verdicts):
                    if isinstance(v, dict):
                        v_str = str(v.get("verdict", "")).lower()
                        if v_str == "rejected":
                            rej += 1
                        elif v_str == "survives":
                            surv += 1
                        elif v_str in ("revised", "revise"):
                            rev += 1

                        if idx not in seen_verdict_indices:
                            seen_verdict_indices.add(idx)
                            v_cand_id = str(v.get("candidate_id", "unknown"))
                            cited = v.get("cited_patents", [])
                            cited_str = f"Prior art: {', '.join(cited)}" if cited else ""
                            
                            _emit_event(
                                job_id,
                                "candidate_challenged",
                                f"Candidate #{v_cand_id} challenged" + (f" ({cited_str})" if cited_str else ""),
                                candidate_id=v_cand_id,
                                evidence=v,
                            )
                            if v_str == "rejected":
                                _emit_event(
                                    job_id,
                                    "candidate_rejected",
                                    f"Candidate #{v_cand_id} rejected",
                                    candidate_id=v_cand_id,
                                    evidence=v,
                                )
                            elif v_str in ("revised", "revise"):
                                _emit_event(
                                    job_id,
                                    "candidate_revised",
                                    f"Candidate #{v_cand_id} revised",
                                    candidate_id=v_cand_id,
                                    evidence=v,
                                )
                            elif v_str == "survives":
                                _emit_event(
                                    job_id,
                                    "candidate_survived",
                                    f"Candidate #{v_cand_id} survived",
                                    candidate_id=v_cand_id,
                                    evidence=v,
                                )

                _jobs[job_id]["progress"]["candidatesRejected"] = rej
                _jobs[job_id]["progress"]["candidatesRevised"] = rev
                _jobs[job_id]["progress"]["candidatesSurvived"] = surv
                
            scores = _as_list(state.get(SCORED_CANDIDATES))
            if scores:
                _jobs[job_id]["stage"] = "governor"
                if not seen_assessment:
                    seen_assessment = True
                    _emit_event(
                        job_id,
                        "assessment_completed",
                        "Final assessment complete",
                        evidence={"scorecardsCount": len(scores)},
                    )

    try:
        await run()
        final = await _session_service.get_session(
            app_name="ip_matchmaker", user_id="web", session_id=session.id
        )
        final_state = final.state or {}
        raw_verdicts = _validated(AdversarialVerdict, final_state.get(ADVERSARIAL_VERDICTS))
        raw_scorecards = _validated(ScoreCard, final_state.get(SCORED_CANDIDATES))
        return {
            "candidates": _validated(InventionCandidate, final_state.get(CANDIDATE_INVENTIONS)),
            "verdicts": reconcile_candidate_verdicts(raw_verdicts, raw_scorecards),
            "scorecards": raw_scorecards,
            "events": _jobs[job_id].get("events", []),
        }
    finally:
        await _session_service.delete_session(
            app_name="ip_matchmaker", user_id="web", session_id=session.id
        )


_QUOTA_FRIENDLY_MESSAGE = (
    "This analysis couldn't be completed because the AI service has reached its "
    "current usage limit. Your research has not been lost — please try again "
    "later, once the quota resets."
)


def _classify_error(exc: Exception) -> dict:
    """Map a raw exception to a user-facing error_type + message.

    Gemini's free tier returns 429 RESOURCE_EXHAUSTED both for short-window
    rate limits (retry-after seconds, fine to auto-retry) and for the daily
    per-project/per-model request cap (retrying does nothing until the quota
    resets). Only the daily-cap message names "PerDay" in its quotaId, so
    that's the signal we key off — an immediate "Try again" is actively
    misleading for that case.
    """
    text = str(exc)
    if "RESOURCE_EXHAUSTED" in text and "PerDay" in text:
        return {"error_type": "quota_exhausted", "detail": _QUOTA_FRIENDLY_MESSAGE}
    return {"error_type": "unknown", "detail": text[:300]}


async def _run_job(job_id: str, req: AnalyzeRequest) -> None:
    async with _analyze_lock:
        try:
            result = await asyncio.wait_for(_execute_analysis(job_id, req), timeout=_ANALYZE_TIMEOUT_S)
            _jobs[job_id] = {
                "status": "done",
                "stage": "done",
                "events": _jobs[job_id].get("events", []),
                **result,
            }
        except TimeoutError:
            _jobs[job_id] = {
                "status": "error",
                "stage": "error",
                "events": _jobs[job_id].get("events", []),
                "error_type": "timeout",
                "detail": f"Agent run exceeded {_ANALYZE_TIMEOUT_S}s.",
            }
        except Exception as exc:
            logger.exception("analyze job %s failed", job_id)
            _jobs[job_id] = {
                "status": "error",
                "stage": "error",
                "events": _jobs[job_id].get("events", []),
                **_classify_error(exc),
            }



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


from fastapi.responses import FileResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402


@app.get("/api/analyze/{job_id}")
async def analyze_status(job_id: str) -> dict:
    """Poll endpoint for a background analyze run."""
    job = _jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Unknown job id.")
    return job


def _get_dist_dir() -> str | None:
    static_dir = os.path.join(AGENTS_DIR, "static")
    if os.path.exists(static_dir):
        return static_dir
    dist_dir = os.path.abspath(os.path.join(AGENTS_DIR, "../frontend/dist"))
    if os.path.exists(dist_dir):
        return dist_dir
    return None


_initial_dist = _get_dist_dir()
if _initial_dist and os.path.exists(os.path.join(_initial_dist, "assets")):
    app.mount("/assets", StaticFiles(directory=os.path.join(_initial_dist, "assets")), name="assets")


@app.get("/")
async def serve_root():
    dist_dir = _get_dist_dir()
    if dist_dir:
        index_file = os.path.join(dist_dir, "index.html")
        if os.path.isfile(index_file):
            return FileResponse(index_file)
    raise HTTPException(
        status_code=404,
        detail="Frontend static build not found. Run 'npm run build' inside frontend/ directory.",
    )


@app.get("/{full_path:path}")
async def serve_frontend(full_path: str):
    if full_path.startswith("api/") or full_path.startswith("health"):
        raise HTTPException(status_code=404, detail="API route not found.")
    dist_dir = _get_dist_dir()
    if dist_dir:
        target_file = os.path.join(dist_dir, full_path)
        if os.path.isfile(target_file):
            return FileResponse(target_file)
        index_file = os.path.join(dist_dir, "index.html")
        if os.path.isfile(index_file):
            return FileResponse(index_file)
    raise HTTPException(status_code=404, detail="Frontend route not found.")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8080")))


