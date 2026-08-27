"""One-command end-to-end validation of the full agent graph against mock data.

Usage: .venv/bin/python run_pipeline.py
Requires a working GEMINI/Vertex express key in .env (Vertex AI API enabled).
Prints each stage's structured output so Days 7-11 DoD can be checked by eye.
"""

import asyncio
import json
import os
import time

from dotenv import load_dotenv

load_dotenv()

from google.adk.plugins.base_plugin import BasePlugin
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from patent_agent.agent import root_agent
from patent_agent.shared.state_keys import (
    ADVERSARIAL_VERDICTS,
    CANDIDATE_INVENTIONS,
    PATENT_LANDSCAPE,
    SCORED_CANDIDATES,
)

PROMPT = (
    "Mine the patent landscape for the locked demo domain "
    "'solid-state battery electrolytes' (query: 'solid electrolyte interphase'). "
    "Cluster into white-space vs saturated areas, propose candidate inventions for "
    "the top white-space cluster, adversarially validate them against prior art, "
    "and score survivors."
)

STATE_KEYS = [PATENT_LANDSCAPE, CANDIDATE_INVENTIONS, ADVERSARIAL_VERDICTS, SCORED_CANDIDATES]


def show(label: str, value):
    print(f"\n=== {label} ===")
    if value is None:
        print("  <missing>")
    elif isinstance(value, str):
        try:
            print(json.dumps(json.loads(value), indent=2)[:2000])
        except json.JSONDecodeError:
            print(value[:2000])
    else:
        print(json.dumps(value, indent=2, default=str)[:2000])


class RateLimiter(BasePlugin):
    """Paces model calls under two limits so free/preview tiers don't 429:
    a minimum gap between calls (RPM-style, what this was originally written
    for on Gemini's free tier) and a token budget over a trailing window
    (TPM-style — Groq's qwen preview caps at 8K tokens/60s). A fixed inter-
    call delay alone isn't enough for TPM caps: two calls individually under
    budget can still sum past it within the same rolling window, which is
    exactly what happened live on Groq. Tunable via env vars so a different
    provider/tier doesn't need a code change.
    """

    def __init__(self) -> None:
        super().__init__(name="rate_limiter")
        self._min_gap = float(os.getenv("RATE_LIMIT_MIN_GAP_SECONDS", "13"))
        self._tpm_budget = int(os.getenv("RATE_LIMIT_TPM_BUDGET", "7000"))
        self._window_seconds = float(os.getenv("RATE_LIMIT_TPM_WINDOW_SECONDS", "60"))
        self._last_call = 0.0
        self._calls: list[tuple[float, int]] = []  # (timestamp, estimated_tokens)

    @staticmethod
    def _estimate_tokens(llm_request) -> int:
        """Rough token proxy (chars/4) over the request's contents/config —
        precise enough to pace calls, not to bill."""
        try:
            text = str(llm_request.contents) + str(llm_request.config)
        except Exception:
            return 2000  # conservative fallback if the request shape ever changes
        return max(len(text) // 4, 1)

    async def before_model_callback(self, *, callback_context, llm_request):
        now = time.monotonic()

        gap_wait = self._last_call + self._min_gap - now
        if gap_wait > 0:
            await asyncio.sleep(gap_wait)
            now = time.monotonic()

        self._calls = [(t, tok) for t, tok in self._calls if now - t < self._window_seconds]
        estimated = self._estimate_tokens(llm_request)
        used = sum(tok for _, tok in self._calls)
        if self._calls and used + estimated > self._tpm_budget:
            budget_wait = self._window_seconds - (now - self._calls[0][0]) + 0.5
            if budget_wait > 0:
                print(f"  [rate-limit] pacing {budget_wait:.0f}s to stay under {self._tpm_budget} TPM...")
                await asyncio.sleep(budget_wait)
                now = time.monotonic()
                self._calls = [(t, tok) for t, tok in self._calls if now - t < self._window_seconds]

        self._last_call = now
        self._calls.append((now, estimated))
        return None


async def main() -> None:
    os.environ.setdefault("USE_MOCK_BIGQUERY", "true")
    session_service = InMemorySessionService()
    runner = Runner(
        agent=root_agent,
        app_name="pipeline_check",
        session_service=session_service,
        plugins=[RateLimiter()],
    )
    session = await session_service.create_session(app_name="pipeline_check", user_id="dev")

    print(f"model={os.getenv('GEMINI_MODEL')} mock_bigquery={os.getenv('USE_MOCK_BIGQUERY')}")
    print("running root_agent (research -> inventor/adversarial loop -> governor)...")

    msg = types.Content(role="user", parts=[types.Part(text=PROMPT)])
    events = 0
    for event in runner.run(user_id="dev", session_id=session.id, new_message=msg):
        events += 1
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    who = event.author or "?"
                    snippet = part.text.strip().replace("\n", " ")[:120]
                    print(f"  [{who}] {snippet}")

    final = await session_service.get_session(
        app_name="pipeline_check", user_id="dev", session_id=session.id
    )
    print(f"\n{events} events total.")
    for key in STATE_KEYS:
        show(key, (final.state or {}).get(key))


if __name__ == "__main__":
    asyncio.run(main())
