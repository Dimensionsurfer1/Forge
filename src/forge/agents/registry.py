from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field


class AgentConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    role: str
    description: str
    default_model: str = "auto"
    skills: list[str] = Field(default_factory=list)
    enabled: bool = True


class AgentRegistry:
    def __init__(self, config_path: str | Path | None = None):
        if config_path is None:
            project_root = Path(__file__).resolve().parents[3]
            config_path = project_root / "config" / "agents.yaml"

        self.config_path = Path(config_path)
        self._agents: dict[str, AgentConfig] = {}
        self.load()

    def load(self) -> None:
        if not self.config_path.exists():
            raise FileNotFoundError(
                f"Agent configuration not found: {self.config_path}"
            )

        with self.config_path.open("r", encoding="utf-8-sig") as file:
            data: Any = yaml.safe_load(file)

        if not isinstance(data, dict) or not isinstance(data.get("agents"), list):
            raise ValueError("Invalid configuration: expected an 'agents' list.")

        agents: dict[str, AgentConfig] = {}

        for item in data["agents"]:
            agent = AgentConfig.model_validate(item)

            if agent.id in agents:
                raise ValueError(f"Duplicate agent ID: {agent.id}")

            agents[agent.id] = agent

        self._agents = agents

    def get(self, agent_id: str) -> AgentConfig:
        try:
            return self._agents[agent_id]
        except KeyError:
            raise KeyError(f"Agent not found: {agent_id}") from None

    def list_agents(self, enabled_only: bool = True) -> list[AgentConfig]:
        agents = list(self._agents.values())

        if enabled_only:
            agents = [agent for agent in agents if agent.enabled]

        return agents

    def __len__(self) -> int:
        return len(self._agents)
