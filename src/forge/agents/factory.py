
from pathlib import Path

from forge.agents.architect.agent import ArchitectAgent
from forge.agents.backend.agent import BackendAgent
from forge.model_router import ModelRouter


def build_agent_handlers(
    router: ModelRouter,
    projects_root: str | Path | None = None,
    allow_file_writes: bool = False,
):
    """Build specialist handlers with project-scoped access."""

    agents = [
        ArchitectAgent(
            router,
            projects_root=projects_root,
            allow_file_writes=allow_file_writes,
        ),
        BackendAgent(
            router,
            projects_root=projects_root,
            allow_file_writes=allow_file_writes,
        ),
    ]

    return {
        agent.agent_id: agent.execute
        for agent in agents
    }
