"""FunctionTool-ready wrappers around the patents data source.

ADK derives each tool's schema from the function signature and docstring, so these
stay thin: validate nothing beyond what the type hints already express, delegate to
get_patents_datasource(), and return plain dicts (LlmAgent tools should not return
Pydantic model instances directly).
"""

from .bigquery_patents import get_patents_datasource
from .clustering import cluster_patents_tool
from .loop_control import exit_loop
from .schemas import PatentRecord

__all__ = [
    "search_patents_tool",
    "get_patent_by_number_tool",
    "get_citations_tool",
    "get_similar_patents_tool",
    "cluster_patents_tool",
    "exit_loop",
]

_ABSTRACT_CHARS = 220  # ponytail: matches tools/context.py's budget


def _compact_record(record: PatentRecord) -> dict:
    """Trims a PatentRecord to what an LLM needs for novelty/prior-art
    judgment, dropping inventors/family_id and truncating the abstract.
    Every tool below returns records in bulk (up to 20 at once), and full
    dumps were the single biggest driver of free-tier TPM overruns."""
    return {
        "publication_number": record.publication_number,
        "title": record.title,
        "abstract": record.abstract[:_ABSTRACT_CHARS],
        "assignee": record.assignee,
        "publication_date": record.publication_date,
        "cpc_codes": record.cpc_codes,
        "citation_count": record.citation_count,
        "similarity_score": record.similarity_score,
    }


def search_patents_tool(query: str, domain: str, max_results: int = 20) -> list[dict]:
    """Search patents matching a free-text query within a technology domain.

    Args:
        query: Free-text search terms (e.g. "solid electrolyte interphase").
        domain: The locked demo technology domain (see docs/roadmap.md).
        max_results: Maximum number of patent records to return.

    Returns:
        A list of compact patent records (publication_number, title, truncated
        abstract, assignee, publication_date, cpc_codes, citation_count,
        similarity_score). Use get_patent_by_number_tool for full detail on one.
    """
    records = get_patents_datasource().search_patents(query, domain, max_results)
    return [_compact_record(r) for r in records]


def get_patent_by_number_tool(publication_number: str) -> dict | None:
    """Fetch one full patent record (all fields) by its publication number
    (e.g. "US-11234567-B2") — use this after search/similar/citations tools
    narrow down a candidate you need full detail on."""
    record = get_patents_datasource().get_patent_by_number(publication_number)
    return record.model_dump() if record else None


def get_citations_tool(publication_number: str) -> list[dict]:
    """Fetch patents cited by the given publication number (compact records —
    see search_patents_tool)."""
    records = get_patents_datasource().get_citations(publication_number)
    return [_compact_record(r) for r in records]


def get_similar_patents_tool(publication_number: str, max_results: int = 5) -> list[dict]:
    """Fetch patents most similar to the given publication number, ranked by
    similarity_score (compact records — see search_patents_tool)."""
    records = get_patents_datasource().get_similar_patents(publication_number, max_results)
    return [_compact_record(r) for r in records]
