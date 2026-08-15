from google.adk.agents import LlmAgent

from ...config import GEMINI_MODEL
from ...shared.state_keys import PATENT_LANDSCAPE
from ...tools import get_citations_tool, get_similar_patents_tool, search_patents_tool
from .prompt import RESEARCH_AGENT_INSTRUCTION

research_agent = LlmAgent(
    name="research_agent",
    model=GEMINI_MODEL,
    instruction=RESEARCH_AGENT_INSTRUCTION,
    tools=[search_patents_tool, get_similar_patents_tool, get_citations_tool],
    output_key=PATENT_LANDSCAPE,
)
