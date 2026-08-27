from google.adk.agents import LlmAgent

from ...config import get_agent_model
from ...shared.state_keys import ADVERSARIAL_VERDICTS
from ...tools import exit_loop, get_citations_tool, get_similar_patents_tool, search_patents_tool
from .prompt import ADVERSARIAL_AGENT_INSTRUCTION

adversarial_agent = LlmAgent(
    name="adversarial_agent",
    model=get_agent_model(),
    instruction=ADVERSARIAL_AGENT_INSTRUCTION,
    tools=[search_patents_tool, get_similar_patents_tool, get_citations_tool, exit_loop],
    output_key=ADVERSARIAL_VERDICTS,
    # ponytail: same fix as inventor_agent — see its include_contents comment.
    include_contents="none",
)
