
from unittest.mock import MagicMock

import pytest

from forge.agents.architect.agent import ArchitectAgent
from forge.agents.backend.agent import BackendAgent
from forge.agents.factory import build_agent_handlers


def make_task():
    return {
        "task_id": "T1",
        "description": "Design the application backend.",
        "priority": "high",
        "dependencies": [],
    }


def test_architect_agent():
    router = MagicMock()
    router.select_model.return_value = "cloud_coding"
    router.chat.return_value = "Architecture design completed."

    agent = ArchitectAgent(router)
    result = agent.execute(make_task())

    assert result["agent_id"] == "architect"
    assert result["model"] == "cloud_coding"
    assert result["content"] == "Architecture design completed."

    router.select_model.assert_called_once_with("architecture")
    router.chat.assert_called_once()


def test_backend_agent():
    router = MagicMock()
    router.select_model.return_value = "cloud_coding"
    router.chat.return_value = "Backend implementation prepared."

    agent = BackendAgent(router)
    result = agent.execute(make_task())

    assert result["agent_id"] == "backend"
    assert result["content"] == "Backend implementation prepared."

    router.select_model.assert_called_once_with(
        "software_development"
    )


def test_agent_rejects_missing_description():
    router = MagicMock()
    agent = ArchitectAgent(router)

    with pytest.raises(ValueError, match="no description"):
        agent.execute({
            "task_id": "T1",
            "description": "",
        })

    router.chat.assert_not_called()


def test_factory_registers_specialist_handlers():
    router = MagicMock()
    handlers = build_agent_handlers(router)

    assert "architect" in handlers
    assert "backend" in handlers
