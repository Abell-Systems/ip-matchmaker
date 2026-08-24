"""Patents data source: a swappable interface over Google Patents Public Datasets.

Defaults to a deterministic mock so the pipeline is developable and demoable before
real GCP/BigQuery credentials exist. Flip USE_MOCK_BIGQUERY=false once they do —
no other code needs to change, since every caller goes through get_patents_datasource().
"""

import os
from typing import Protocol

from .fixtures import generate_patents
from .schemas import PatentRecord


class PatentsDataSource(Protocol):
    def search_patents(self, query: str, domain: str, max_results: int = 20) -> list[PatentRecord]: ...

    def get_patent_by_number(self, publication_number: str) -> PatentRecord | None: ...

    def get_citations(self, publication_number: str) -> list[PatentRecord]: ...

    def get_similar_patents(self, publication_number: str, max_results: int = 10) -> list[PatentRecord]: ...


class MockPatentsDataSource:
    """Deterministic fake data source — no network or credentials required."""

    def search_patents(self, query: str, domain: str, max_results: int = 20) -> list[PatentRecord]:
        return generate_patents(query, domain, max_results)

    def get_patent_by_number(self, publication_number: str) -> PatentRecord | None:
        records = generate_patents(publication_number, "generic", 1)
        record = records[0]
        return record.model_copy(update={"publication_number": publication_number})

    def get_citations(self, publication_number: str) -> list[PatentRecord]:
        return generate_patents(f"citations-of-{publication_number}", "generic", 5)

    def get_similar_patents(self, publication_number: str, max_results: int = 10) -> list[PatentRecord]:
        records = generate_patents(f"similar-to-{publication_number}", "generic", max_results)
        for i, record in enumerate(records):
            records[i] = record.model_copy(update={"similarity_score": round(0.95 - i * 0.05, 2)})
        return records


class BigQueryPatentsDataSource:
    """Real implementation, querying patents-public-data on BigQuery.

    Constructed lazily by get_patents_datasource() so google-cloud-bigquery import
    and auth only happen when USE_MOCK_BIGQUERY=false.
    """

    def __init__(self, project: str):
        from google.cloud import bigquery

        self._client = bigquery.Client(project=project)

    def search_patents(self, query: str, domain: str, max_results: int = 20) -> list[PatentRecord]:
        raise NotImplementedError("Real BigQuery search_patents not implemented yet (Day 1-3 work).")

    def get_patent_by_number(self, publication_number: str) -> PatentRecord | None:
        raise NotImplementedError("Real BigQuery get_patent_by_number not implemented yet (Day 1-3 work).")

    def get_citations(self, publication_number: str) -> list[PatentRecord]:
        raise NotImplementedError("Real BigQuery get_citations not implemented yet (Day 1-3 work).")

    def get_similar_patents(self, publication_number: str, max_results: int = 10) -> list[PatentRecord]:
        raise NotImplementedError("Real BigQuery get_similar_patents not implemented yet (Day 1-3 work).")


def get_patents_datasource() -> PatentsDataSource:
    if os.getenv("USE_MOCK_BIGQUERY", "true").lower() == "true":
        return MockPatentsDataSource()
    project = os.getenv("GOOGLE_CLOUD_PROJECT")
    if not project:
        raise RuntimeError(
            "USE_MOCK_BIGQUERY=false requires GOOGLE_CLOUD_PROJECT to be set "
            "(and BigQuery credentials to be available)."
        )
    return BigQueryPatentsDataSource(project=project)
