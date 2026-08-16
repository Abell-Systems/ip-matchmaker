"""Demand-signal data source: a swappable interface over open technology-need feeds
(SBIR.gov Topic API, CORDIS Data Extraction Tool API).

Defaults to a deterministic mock so the pipeline is developable and demoable before
real API access exists. Flip USE_MOCK_DEMAND=false once real source implementations
land — no other code needs to change, since every caller goes through
get_demand_datasource().
"""

import os
from typing import Protocol

from .demand_fixtures import generate_demand_signals
from .schemas import DemandSignal


class DemandDataSource(Protocol):
    def search_demand(self, query: str, domain: str, max_results: int = 20) -> list[DemandSignal]: ...


class MockDemandDataSource:
    """Deterministic fake data source — no network or credentials required."""

    def search_demand(self, query: str, domain: str, max_results: int = 20) -> list[DemandSignal]:
        return generate_demand_signals(query, domain, max_results)


class SBIRDemandDataSource:
    """Real implementation, querying the SBIR.gov Topic API."""

    def search_demand(self, query: str, domain: str, max_results: int = 20) -> list[DemandSignal]:
        raise NotImplementedError("Real SBIR.gov search_demand not implemented yet.")


class CORDISDemandDataSource:
    """Real implementation, querying the CORDIS Data Extraction Tool API."""

    def search_demand(self, query: str, domain: str, max_results: int = 20) -> list[DemandSignal]:
        raise NotImplementedError("Real CORDIS search_demand not implemented yet.")


def get_demand_datasource() -> DemandDataSource:
    if os.getenv("USE_MOCK_DEMAND", "true").lower() == "true":
        return MockDemandDataSource()
    raise NotImplementedError("Real demand sources (SBIR/CORDIS) not wired up yet.")
