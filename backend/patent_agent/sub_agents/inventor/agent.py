from google.adk.agents import LlmAgent

from ...config import get_agent_model
from ...shared.state_keys import CANDIDATE_INVENTIONS
from ...tools.schemas import InventionCandidate
from .prompt import INVENTOR_AGENT_INSTRUCTION

inventor_agent = LlmAgent(
    name="inventor_agent",
    model=get_agent_model(),
    instruction=INVENTOR_AGENT_INSTRUCTION,
    tools=[],
    output_key=CANDIDATE_INVENTIONS,
    output_schema=InventionCandidate,
)
