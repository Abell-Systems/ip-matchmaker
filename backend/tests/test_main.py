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
