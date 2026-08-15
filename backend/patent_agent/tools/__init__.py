"""FunctionTool-ready wrappers around the patents data source.

ADK derives each tool's schema from the function signature and docstring, so these
stay thin: validate nothing beyond what the type hints already express, delegate to
get_patents_datasource(), and return plain dicts (LlmAgent tools should not return
Pydantic model instances directly).

The Day 4-6 landscape-clustering FunctionTool (embeddings + clustering over
search_patents_tool results) is not implemented yet — it lands with the Days 4-6
work per docs/roadmap.md, as a sibling function in this package.
"""

from .bigquery_patents import get_patents_datasource
from .loop_control import exit_loop

__all__ = [
    "search_patents_tool",
    "get_patent_by_number_tool",
    "get_citations_tool",
    "get_similar_patents_tool",
    "exit_loop",
]


def search_patents_tool(query: str, domain: str, max_results: int = 20) -> list[dict]:
    """Search patents matching a free-text query within a technology domain.

    Args:
        query: Free-text search terms (e.g. "solid electrolyte interphase").
        domain: The locked demo technology domain (see docs/roadmap.md).
        max_results: Maximum number of patent records to return.

    Returns:
        A list of patent records (publication_number, title, abstract, assignee,
        inventors, filing/publication dates, cpc_codes, etc).
    """
    records = get_patents_datasource().search_patents(query, domain, max_results)
    return [r.model_dump() for r in records]


def get_patent_by_number_tool(publication_number: str) -> dict | None:
    """Fetch a single patent record by its publication number (e.g. "US-11234567-B2")."""
    record = get_patents_datasource().get_patent_by_number(publication_number)
    return record.model_dump() if record else None


def get_citations_tool(publication_number: str) -> list[dict]:
    """Fetch patents cited by the given publication number."""
    records = get_patents_datasource().get_citations(publication_number)
    return [r.model_dump() for r in records]


def get_similar_patents_tool(publication_number: str, max_results: int = 10) -> list[dict]:
    """Fetch patents most similar to the given publication number, ranked by similarity_score."""
    records = get_patents_datasource().get_similar_patents(publication_number, max_results)
    return [r.model_dump() for r in records]
