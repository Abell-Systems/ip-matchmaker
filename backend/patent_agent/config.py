"""Environment-driven configuration shared by all agents."""

import os
from .provider import LLMProvider

USE_MOCK_BIGQUERY = os.getenv("USE_MOCK_BIGQUERY", "true").lower() == "true"
USE_MOCK_DEMAND = os.getenv("USE_MOCK_DEMAND", "true").lower() == "true"
GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT")
GOOGLE_CLOUD_LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")

INVENTION_LOOP_MAX_ITERATIONS = int(os.getenv("INVENTION_LOOP_MAX_ITERATIONS", "4"))


def get_agent_model():
    """Returns the model value every LlmAgent is constructed with."""
    return LLMProvider.get_agent_model()
