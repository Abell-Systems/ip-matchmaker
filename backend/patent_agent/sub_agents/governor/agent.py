from google.adk.agents import LlmAgent

from ...config import get_agent_model
from ...shared.state_keys import SCORED_CANDIDATES
from ...tools.schemas import ScoreCardList
from .prompt import GOVERNOR_AGENT_INSTRUCTION

governor_agent = LlmAgent(
    name="governor_agent",
    model=get_agent_model(),
    instruction=GOVERNOR_AGENT_INSTRUCTION,
    tools=[],
    output_key=SCORED_CANDIDATES,
    output_schema=ScoreCardList,
)
