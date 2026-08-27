"""Environment-driven configuration shared by all agents."""

import os

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
USE_MOCK_BIGQUERY = os.getenv("USE_MOCK_BIGQUERY", "true").lower() == "true"
USE_MOCK_DEMAND = os.getenv("USE_MOCK_DEMAND", "true").lower() == "true"
GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT")
GOOGLE_CLOUD_LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")

INVENTION_LOOP_MAX_ITERATIONS = int(os.getenv("INVENTION_LOOP_MAX_ITERATIONS", "4"))

# MODEL_PROVIDER selects which backend LlmAgents call: "gemini" (default, used by
# the Cloud Run demo path) or "openrouter" (dev-validation path that avoids
# burning GEMINI_API_KEY's free-tier quota — see render.yaml).
MODEL_PROVIDER = os.getenv("MODEL_PROVIDER", "gemini").lower()
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "z-ai/glm-5.2:free")


def get_agent_model():
    """Returns the model value every LlmAgent is constructed with.

    A plain string for Gemini (ADK resolves it natively); a LiteLlm instance
    routed through OpenRouter's OpenAI-compatible API otherwise.
    """
    if MODEL_PROVIDER == "openrouter":
        from google.adk.models.lite_llm import LiteLlm

        return LiteLlm(model=f"openrouter/{OPENROUTER_MODEL}")
    return GEMINI_MODEL
