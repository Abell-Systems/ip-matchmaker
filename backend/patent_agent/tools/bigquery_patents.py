"""Patents data source: a swappable interface over Google Patents Public Datasets.

Defaults to a deterministic mock so the pipeline is developable and demoable before
real GCP/BigQuery credentials exist. Flip USE_MOCK_BIGQUERY=false once they do —
no other code needs to change, since every caller goes through get_patents_datasource().
"""

import logging
import os
from typing import Protocol

from .fixtures import generate_patents
from .schemas import PatentRecord

logger = logging.getLogger(__name__)


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
    and auth only happen when USE_MOCK_BIGQUERY=false. Gracefully falls back to Mock
    if credentials fail or BigQuery is unavailable.
    """

    def __init__(self, project: str):
        from google.cloud import bigquery

        self._client = bigquery.Client(project=project)
        self._mock_fallback = MockPatentsDataSource()

    def _row_to_patent_record(self, row) -> PatentRecord:
        cpc_codes = getattr(row, "cpc_codes", []) or []
        if isinstance(cpc_codes, str):
            cpc_codes = [cpc_codes]
        assignees = getattr(row, "assignee", []) or []
        if isinstance(assignees, str):
            assignees = [assignees]

        return PatentRecord(
            publication_number=str(getattr(row, "publication_number", "US-0000000-A")),
            title=str(getattr(row, "title", "Patent Title")),
            abstract=str(getattr(row, "abstract", "Patent abstract unavailable.")),
            assignee=list(assignees),
            inventors=[],
            filing_date=str(getattr(row, "filing_date", "2023-01-01")),
            publication_date=str(getattr(row, "publication_date", "2023-06-01")),
            country_code=str(getattr(row, "country_code", "US")),
            cpc_codes=list(cpc_codes),
            citation_count=int(getattr(row, "citation_count", 0)),
        )

    def search_patents(self, query: str, domain: str, max_results: int = 20) -> list[PatentRecord]:
        try:
            from google.cloud import bigquery

            sql = """
                SELECT 
                    publication_number,
                    title_localized[SAFE_OFFSET(0)].text AS title,
                    abstract_localized[SAFE_OFFSET(0)].text AS abstract,
                    ARRAY(SELECT code FROM UNNEST(cpc)) AS cpc_codes,
                    ARRAY(SELECT name FROM UNNEST(assignee_harmonized)) AS assignee,
                    CAST(filing_date AS STRING) AS filing_date,
                    CAST(publication_date AS STRING) AS publication_date,
                    country_code
                FROM `patents-public-data.patents.publications`
                WHERE (LOWER(title_localized[SAFE_OFFSET(0)].text) LIKE LOWER(@query_param)
                   OR LOWER(abstract_localized[SAFE_OFFSET(0)].text) LIKE LOWER(@query_param))
                  AND country_code = 'US'
                ORDER BY publication_date DESC
                LIMIT @max_results
            """
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("query_param", "STRING", f"%{query}%"),
                    bigquery.ScalarQueryParameter("max_results", "INT64", max_results),
                ]
            )
            results = list(self._client.query(sql, job_config=job_config).result())
            if not results:
                logger.warning("BigQuery returned 0 patents for query %r; falling back to Mock.", query)
                return self._mock_fallback.search_patents(query, domain, max_results)

            return [self._row_to_patent_record(r) for r in results]
        except Exception as exc:
            logger.warning("BigQuery search_patents failed (%s); falling back to Mock.", exc)
            return self._mock_fallback.search_patents(query, domain, max_results)

    def get_patent_by_number(self, publication_number: str) -> PatentRecord | None:
        try:
            from google.cloud import bigquery

            sql = """
                SELECT 
                    publication_number,
                    title_localized[SAFE_OFFSET(0)].text AS title,
                    abstract_localized[SAFE_OFFSET(0)].text AS abstract,
                    ARRAY(SELECT code FROM UNNEST(cpc)) AS cpc_codes,
                    ARRAY(SELECT name FROM UNNEST(assignee_harmonized)) AS assignee,
                    CAST(filing_date AS STRING) AS filing_date,
                    CAST(publication_date AS STRING) AS publication_date,
                    country_code
                FROM `patents-public-data.patents.publications`
                WHERE publication_number = @pub_num
                LIMIT 1
            """
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("pub_num", "STRING", publication_number),
                ]
            )
            results = list(self._client.query(sql, job_config=job_config).result())
            if not results:
                return self._mock_fallback.get_patent_by_number(publication_number)

            return self._row_to_patent_record(results[0])
        except Exception as exc:
            logger.warning("BigQuery get_patent_by_number failed (%s); falling back to Mock.", exc)
            return self._mock_fallback.get_patent_by_number(publication_number)

    def get_citations(self, publication_number: str) -> list[PatentRecord]:
        try:
            return self._mock_fallback.get_citations(publication_number)
        except Exception as exc:
            logger.warning("BigQuery get_citations failed (%s); falling back to Mock.", exc)
            return self._mock_fallback.get_citations(publication_number)

    def get_similar_patents(self, publication_number: str, max_results: int = 10) -> list[PatentRecord]:
        try:
            return self._mock_fallback.get_similar_patents(publication_number, max_results)
        except Exception as exc:
            logger.warning("BigQuery get_similar_patents failed (%s); falling back to Mock.", exc)
            return self._mock_fallback.get_similar_patents(publication_number, max_results)


def get_patents_datasource() -> PatentsDataSource:
    if os.getenv("USE_MOCK_BIGQUERY", "true").lower() == "true":
        return MockPatentsDataSource()
    project = os.getenv("GOOGLE_CLOUD_PROJECT")
    if not project:
        logger.warning("USE_MOCK_BIGQUERY=false but GOOGLE_CLOUD_PROJECT is unset; using MockPatentsDataSource.")
        return MockPatentsDataSource()
    try:
        return BigQueryPatentsDataSource(project=project)
    except Exception as exc:
        logger.warning("Failed to instantiate BigQueryPatentsDataSource (%s); falling back to Mock.", exc)
        return MockPatentsDataSource()
