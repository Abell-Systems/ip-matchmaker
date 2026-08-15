"""Environment-driven configuration shared by all agents."""

import os

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
USE_MOCK_BIGQUERY = os.getenv("USE_MOCK_BIGQUERY", "true").lower() == "true"
GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT")
GOOGLE_CLOUD_LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")

INVENTION_LOOP_MAX_ITERATIONS = int(os.getenv("INVENTION_LOOP_MAX_ITERATIONS", "4"))
