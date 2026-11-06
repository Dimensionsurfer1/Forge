
from forge.agents.architect.agent import ArchitectAgent
from forge.agents.backend.agent import BackendAgent
from forge.model_router import ModelRouter


def build_agent_handlers(router: ModelRouter):
    """Create the handlers used by Forge's AgentExecutor."""

    agents = [
        ArchitectAgent(router),
        BackendAgent(router),
    ]

    return {
        agent.agent_id: agent.execute
        for agent in agents
    }
