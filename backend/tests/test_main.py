import os

os.environ.setdefault("USE_MOCK_BIGQUERY", "true")

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_analyze_rejects_empty_input_before_llm_call(monkeypatch):
    # The real agent graph needs a live Gemini key; skip calling it in unit
    # tests and instead assert the endpoint exists and validates its input.
    response = client.post("/api/analyze", json={"query": "", "domain": "", "cluster_id": ""})
    assert response.status_code == 422  # empty query/domain rejected before an LLM call is made


def test_as_list_normalizes_state_shapes():
    from main import _as_list

    assert _as_list(None) == []
    assert _as_list('{"candidate_id": "c1"}') == [{"candidate_id": "c1"}]
    assert _as_list({"candidate_id": "c1"}) == [{"candidate_id": "c1"}]
    assert _as_list({"scorecards": [{"novelty": 0.9}]}) == [{"novelty": 0.9}]
    assert _as_list("plain adversarial prose") == ["plain adversarial prose"]
    assert _as_list([{"a": 1}]) == [{"a": 1}]


def test_validated_drops_malformed_entries():
    from main import _validated
    from patent_agent.tools.schemas import ScoreCard

    good = {
        "candidate_id": "c1",
        "novelty": 0.9,
        "prior_art_risk": 0.1,
        "differentiation": 0.8,
        "evidence": 0.7,
        "supporting_evidence": ["US-1"],
        "summary": "ok",
    }
    # free-text agent output and missing required fields must not reach the frontend
    out = _validated(ScoreCard, [good, "prose", {"candidate_id": "c2"}, dict(good, novelty="high")])
    assert out == [good]


def test_landscape_rejects_invalid_params():
    assert client.get("/api/landscape", params={"query": "", "domain": "d"}).status_code == 422
    assert client.get("/api/landscape", params={"query": "q", "domain": ""}).status_code == 422
    assert (
        client.get("/api/landscape", params={"query": "q", "domain": "d", "max_results": 1000}).status_code
        == 422
    )


def test_landscape_single_search_and_valid_clusters():
    from patent_agent.tools.schemas import PatentCluster, PatentRecord

    calls: list[tuple[str, int]] = []

    class SpySource:
        def search_patents(self, query, domain, max_results=20):
            calls.append((query, max_results))
            return [
                PatentRecord(
                    publication_number=f"US-{i}",
                    title=f"t{i}",
                    abstract="a",
                    filing_date="2025-01-01",
                    publication_date="2025-06-01",
                    country_code="US",
                    cpc_codes=["H01M10/0562"],
                )
                for i in range(3)
            ]

    import main

    original = main.get_patents_datasource
    main.get_patents_datasource = lambda: SpySource()
    try:
        response = client.get("/api/landscape", params={"query": "q", "domain": "d"})
    finally:
        main.get_patents_datasource = original
    assert response.status_code == 200
    body = response.json()
    assert len(calls) == 1  # patents searched once, not again for clustering
    assert body["clusters"]
    PatentCluster.model_validate(body["clusters"][0])
