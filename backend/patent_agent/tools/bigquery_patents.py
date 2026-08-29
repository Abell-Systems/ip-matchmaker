"""Patents data source: a swappable interface over Google Patents Public Datasets.

Defaults to a deterministic mock so the pipeline is developable and demoable before
real GCP/BigQuery credentials exist. Flip USE_MOCK_BIGQUERY=false once they do —
no other code needs to change, since every caller goes through get_patents_datasource().
"""

import logging
import os
import time
from typing import Any, Protocol

from .fixtures import generate_patents
from .schemas import PatentRecord

logger = logging.getLogger(__name__)

# patents-public-data.patents.publications is multi-terabyte; /api/landscape is a
# public, unauthenticated endpoint, so every query needs a hard cost ceiling. A
# breached cap raises before billing anything and is caught by the existing
# fallback-to-mock handling below -- never a 500, just degraded data.
_DEFAULT_MAX_BYTES_BILLED = 1_000_000_000  # 1 GB; tune after a real dry-run (see docs/deploy.md)
_DEFAULT_CACHE_TTL_SECONDS = 3600.0
_CITATIONS_LIMIT = 20  # get_citations has no caller-supplied max_results; matches search's default


def _max_bytes_billed() -> int:
    return int(os.getenv("BIGQUERY_MAX_BYTES_BILLED", str(_DEFAULT_MAX_BYTES_BILLED)))


def _cache_ttl_seconds() -> float:
    return float(os.getenv("BIGQUERY_CACHE_TTL_SECONDS", str(_DEFAULT_CACHE_TTL_SECONDS)))


_MISSING = object()


class _TTLCache:
    """Minimal in-process TTL cache. Only ever holds genuine BigQuery results
    (see call sites) -- a mock fallback is already free, so caching it would
    only risk serving stale mock data once BigQuery recovers."""

    def __init__(self, ttl_seconds: float):
        self._ttl = ttl_seconds
        self._store: dict[Any, tuple[float, Any]] = {}

    def get(self, key: Any) -> Any:
        entry = self._store.get(key)
        if entry is None:
            return _MISSING
        expires_at, value = entry
        if time.monotonic() >= expires_at:
            del self._store[key]
            return _MISSING
        return value

    def set(self, key: Any, value: Any) -> None:
        self._store[key] = (time.monotonic() + self._ttl, value)


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

    def get_status(self) -> dict:
        return {"type": "mock", "last_query_source": "mock"}


class BigQueryPatentsDataSource:
    """Real implementation, querying patents-public-data on BigQuery.

    Constructed lazily by get_patents_datasource() so google-cloud-bigquery import
    and auth only happen when USE_MOCK_BIGQUERY=false. Gracefully falls back to Mock
    if credentials fail or BigQuery is unavailable.
    """

    def __init__(self, project: str):
        from google.cloud import bigquery

        self._mock_fallback = MockPatentsDataSource()
        self._search_cache = _TTLCache(_cache_ttl_seconds())
        self._patent_cache = _TTLCache(_cache_ttl_seconds())
        self._citations_cache = _TTLCache(_cache_ttl_seconds())
        # Set on every call so /health can report whether the last request actually
        # reached BigQuery or silently degraded to mock data.
        self.last_result_source = "not_yet_queried"
        try:
            self._client = bigquery.Client(project=project)
        except Exception:
            logger.warning("BigQuery client init failed, falling back to mock data", exc_info=True)
            self._client = None

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
        cache_key = (query, domain, max_results)
        cached = self._search_cache.get(cache_key)
        if cached is not _MISSING:
            self.last_result_source = "bigquery_cached"
            return cached

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
                ],
                maximum_bytes_billed=_max_bytes_billed(),
            )
            results = list(self._client.query(sql, job_config=job_config).result())
            if not results:
                logger.warning("BigQuery returned 0 patents for query %r; falling back to Mock.", query)
                self.last_result_source = "mock_fallback"
                return self._mock_fallback.search_patents(query, domain, max_results)

            records = [self._row_to_patent_record(r) for r in results]
            self.last_result_source = "bigquery"
            self._search_cache.set(cache_key, records)
            return records
        except Exception as exc:
            logger.warning("BigQuery search_patents failed (%s); falling back to Mock.", exc)
            self.last_result_source = "mock_fallback"
            return self._mock_fallback.search_patents(query, domain, max_results)

    def get_patent_by_number(self, publication_number: str) -> PatentRecord | None:
        cached = self._patent_cache.get(publication_number)
        if cached is not _MISSING:
            self.last_result_source = "bigquery_cached"
            return cached

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
                ],
                maximum_bytes_billed=_max_bytes_billed(),
            )
            results = list(self._client.query(sql, job_config=job_config).result())
            if not results:
                self.last_result_source = "mock_fallback"
                return self._mock_fallback.get_patent_by_number(publication_number)

            record = self._row_to_patent_record(results[0])
            self.last_result_source = "bigquery"
            self._patent_cache.set(publication_number, record)
            return record
        except Exception as exc:
            logger.warning("BigQuery get_patent_by_number failed (%s); falling back to Mock.", exc)
            self.last_result_source = "mock_fallback"
            return self._mock_fallback.get_patent_by_number(publication_number)

    def get_citations(self, publication_number: str) -> list[PatentRecord]:
        cached = self._citations_cache.get(publication_number)
        if cached is not _MISSING:
            self.last_result_source = "bigquery_cached"
            return cached

        try:
            from google.cloud import bigquery

            # `citation` is a repeated field already present on every publications
            # row (patents-public-data's own schema) -- self-join back onto the
            # same table to resolve each cited publication_number to a full
            # record in one query, rather than one query per citation.
            sql = """
                SELECT
                    cited.publication_number AS publication_number,
                    cited.title_localized[SAFE_OFFSET(0)].text AS title,
                    cited.abstract_localized[SAFE_OFFSET(0)].text AS abstract,
                    ARRAY(SELECT code FROM UNNEST(cited.cpc)) AS cpc_codes,
                    ARRAY(SELECT name FROM UNNEST(cited.assignee_harmonized)) AS assignee,
                    CAST(cited.filing_date AS STRING) AS filing_date,
                    CAST(cited.publication_date AS STRING) AS publication_date,
                    cited.country_code AS country_code
                FROM `patents-public-data.patents.publications` AS src,
                UNNEST(src.citation) AS cite
                JOIN `patents-public-data.patents.publications` AS cited
                    ON cited.publication_number = cite.publication_number
                WHERE src.publication_number = @pub_num
                LIMIT @max_results
            """
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("pub_num", "STRING", publication_number),
                    bigquery.ScalarQueryParameter("max_results", "INT64", _CITATIONS_LIMIT),
                ],
                maximum_bytes_billed=_max_bytes_billed(),
            )
            results = list(self._client.query(sql, job_config=job_config).result())
            if not results:
                self.last_result_source = "mock_fallback"
                return self._mock_fallback.get_citations(publication_number)

            records = [self._row_to_patent_record(r) for r in results]
            self.last_result_source = "bigquery"
            self._citations_cache.set(publication_number, records)
            return records
        except Exception as exc:
            logger.warning("BigQuery get_citations failed (%s); falling back to Mock.", exc)
            self.last_result_source = "mock_fallback"
            return self._mock_fallback.get_citations(publication_number)

    def get_similar_patents(self, publication_number: str, max_results: int = 10) -> list[PatentRecord]:
        # Not yet wired to a real BigQuery query -- always mock. See get_status().
        # Unlike citations, real similarity needs google_patents_research.publications'
        # precomputed embedding/similarity fields -- a second table, held for later.
        return self._mock_fallback.get_similar_patents(publication_number, max_results)

    def get_status(self) -> dict:
        return {
            "type": "bigquery",
            "last_query_source": self.last_result_source,
            "search_patents_backed_by": "bigquery",
            "get_patent_by_number_backed_by": "bigquery",
            "get_citations_backed_by": "bigquery",
            "get_similar_patents_backed_by": "mock",
        }


_datasource_singleton: PatentsDataSource | None = None


def get_patents_datasource() -> PatentsDataSource:
    """Memoized so the TTL cache and the BigQuery client survive across requests
    instead of being rebuilt (and re-authenticated) on every call -- Cloud Run
    deploys here are pinned to --max-instances=1, so one process-wide instance
    is safe (same rationale as the in-memory job store; see docs/architecture.md)."""
    global _datasource_singleton
    if _datasource_singleton is not None:
        return _datasource_singleton

    if os.getenv("USE_MOCK_BIGQUERY", "true").lower() == "true":
        _datasource_singleton = MockPatentsDataSource()
        return _datasource_singleton

    project = os.getenv("GOOGLE_CLOUD_PROJECT")
    if not project:
        logger.warning("USE_MOCK_BIGQUERY=false but GOOGLE_CLOUD_PROJECT is unset; using MockPatentsDataSource.")
        _datasource_singleton = MockPatentsDataSource()
        return _datasource_singleton

    try:
        _datasource_singleton = BigQueryPatentsDataSource(project=project)
    except Exception as exc:
        logger.warning("Failed to instantiate BigQueryPatentsDataSource (%s); falling back to Mock.", exc)
        _datasource_singleton = MockPatentsDataSource()
    return _datasource_singleton
