from google.adk.agents import LlmAgent

from ...config import GEMINI_MODEL
from ...shared.state_keys import SCORED_CANDIDATES
from .prompt import GOVERNOR_AGENT_INSTRUCTION

governor_agent = LlmAgent(
    name="governor_agent",
    model=GEMINI_MODEL,
    instruction=GOVERNOR_AGENT_INSTRUCTION,
    tools=[],
    output_key=SCORED_CANDIDATES,
)
