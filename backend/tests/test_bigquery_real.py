import pytest
from unittest.mock import MagicMock
from patent_agent.tools.bigquery_patents import BigQueryPatentsDataSource, get_patents_datasource
from patent_agent.tools.schemas import PatentRecord


def test_bigquery_search_patents_fallback_on_error():
    ds = BigQueryPatentsDataSource(project="test-project")
    # Simulate client throwing an Exception (e.g., auth failure or quota error)
    ds._client = MagicMock()
    ds._client.query.side_effect = Exception("BigQuery connection error")

    records = ds.search_patents("solid electrolyte", "batteries", max_results=5)
    assert len(records) > 0
    assert isinstance(records[0], PatentRecord)
    assert records[0].publication_number is not None


def test_bigquery_get_patent_by_number_fallback():
    ds = BigQueryPatentsDataSource(project="test-project")
    ds._client = MagicMock()
    ds._client.query.side_effect = Exception("BigQuery error")

    patent = ds.get_patent_by_number("US-1234567-A")
    assert patent is not None
    assert patent.publication_number == "US-1234567-A"


def test_bigquery_get_citations_fallback():
    ds = BigQueryPatentsDataSource(project="test-project")
    ds._client = MagicMock()
    ds._client.query.side_effect = Exception("BigQuery error")

    citations = ds.get_citations("US-1234567-A")
    assert isinstance(citations, list)
    assert len(citations) > 0


def test_bigquery_get_similar_patents_fallback():
    ds = BigQueryPatentsDataSource(project="test-project")
    ds._client = MagicMock()
    ds._client.query.side_effect = Exception("BigQuery error")

    similar = ds.get_similar_patents("US-1234567-A", max_results=3)
    assert isinstance(similar, list)
    assert len(similar) > 0
