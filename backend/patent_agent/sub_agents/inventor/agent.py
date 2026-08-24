from google.adk.agents import LlmAgent

from ...config import GEMINI_MODEL
from ...shared.state_keys import CANDIDATE_INVENTIONS
from ...tools.schemas import InventionCandidate
from .prompt import INVENTOR_AGENT_INSTRUCTION

inventor_agent = LlmAgent(
    name="inventor_agent",
    model=GEMINI_MODEL,
    instruction=INVENTOR_AGENT_INSTRUCTION,
    tools=[],
    output_key=CANDIDATE_INVENTIONS,
    output_schema=InventionCandidate,
)
