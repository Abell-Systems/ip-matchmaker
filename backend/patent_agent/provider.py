"""LLM Provider abstraction layer.

Resolves model instances and configuration for Google ADK agents based on environment settings.
Supports standard environment trio: MODEL_PROVIDER, MODEL_NAME, MODEL_KEY.
Fails fast on unknown or unsupported providers.
"""

import os
from typing import Any, Dict, List, Set, Union

SUPPORTED_PROVIDERS: Set[str] = {"gemini", "groq", "openrouter", "openai", "anthropic"}

DEFAULT_MODELS: Dict[str, str] = {
    "gemini": "gemini-3.5-flash",
    "groq": "qwen/qwen3-32b",
    "openrouter": "minimax/minimax-m2.7:free",
    "openai": "gpt-4o-mini",
    "anthropic": "claude-3-5-haiku-20241022",
}

API_KEY_ENV_VARS: Dict[str, List[str]] = {
    "gemini": ["GEMINI_API_KEY", "GOOGLE_API_KEY"],
    "groq": ["GROQ_API_KEY"],
    "openrouter": ["OPENROUTER_API_KEY"],
    "openai": ["OPENAI_API_KEY"],
    "anthropic": ["ANTHROPIC_API_KEY"],
}


class LLMProvider:
    """Single source of truth for resolving LLM models across the application."""

    @classmethod
    def get_provider_name(cls) -> str:
        """Returns the normalized provider name from environment, failing fast if unsupported."""
        provider = os.getenv("MODEL_PROVIDER", "gemini").lower().strip()
        if provider not in SUPPORTED_PROVIDERS:
            supported = ", ".join(sorted(SUPPORTED_PROVIDERS))
            raise ValueError(f"Unsupported MODEL_PROVIDER: '{provider}'. Supported providers are: {supported}.")
        return provider

    @classmethod
    def get_model_name(cls) -> str:
        """Returns the model name for the current provider."""
        provider = cls.get_provider_name()
        model_name = (
            os.getenv("MODEL_NAME")
            or os.getenv(f"{provider.upper()}_MODEL")
            or DEFAULT_MODELS.get(provider)
        )
        if not model_name:
            raise ValueError(f"No model configured for provider '{provider}'.")
        return model_name

    @classmethod
    def sync_model_key(cls) -> None:
        """Propagates generic MODEL_KEY env var to provider-specific SDK env vars if set."""
        model_key = os.getenv("MODEL_KEY")
        if not model_key:
            return

        provider = cls.get_provider_name()
        target_vars = API_KEY_ENV_VARS.get(provider, [f"{provider.upper()}_API_KEY"])
        for var in target_vars:
            if not os.getenv(var):
                os.environ[var] = model_key

    @classmethod
    def get_agent_model(cls) -> Union[str, Any]:
        """Resolves the model object expected by ADK LlmAgent.

        Returns:
            str for Gemini (native ADK format)
            LiteLlm instance for all other providers (groq, openrouter, openai, etc.)
        """
        cls.sync_model_key()
        provider = cls.get_provider_name()
        model_name = cls.get_model_name()

        if provider == "gemini":
            return model_name

        from google.adk.models.lite_llm import LiteLlm

        if model_name.startswith(f"{provider}/"):
            model_id = model_name
        else:
            model_id = f"{provider}/{model_name}"

        return LiteLlm(model=model_id)

    @classmethod
    def is_api_key_configured(cls) -> bool:
        """Checks if an API key environment variable is present for the active provider."""
        if bool(os.getenv("MODEL_KEY")):
            return True
        provider = cls.get_provider_name()
        env_vars = API_KEY_ENV_VARS.get(provider, [f"{provider.upper()}_API_KEY"])
        return any(bool(os.getenv(var)) for var in env_vars)

    @classmethod
    def get_status(cls) -> Dict[str, Any]:
        """Returns provider, model, and configuration metadata for health/monitoring endpoints."""
        return {
            "model_provider": cls.get_provider_name(),
            "model": cls.get_model_name(),
            "api_key_configured": cls.is_api_key_configured(),
        }
