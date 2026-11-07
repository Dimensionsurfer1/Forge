
import json
from pathlib import Path
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


def make_response(summary):
    return json.dumps({
        "summary": summary,
        "file_changes": [],
    })


def test_architect_agent():
    router = MagicMock()
    router.select_model.return_value = "cloud_coding"
    router.chat.return_value = make_response(
        "Architecture design completed."
    )

    agent = ArchitectAgent(router)
    result = agent.execute(make_task())

    assert result["agent_id"] == "architect"
    assert result["model"] == "cloud_coding"
    assert result["summary"] == "Architecture design completed."

    router.select_model.assert_called_once_with("architecture")
    router.chat.assert_called_once()


def test_backend_agent():
    router = MagicMock()
    router.select_model.return_value = "cloud_coding"
    router.chat.return_value = make_response(
        "Backend implementation prepared."
    )

    agent = BackendAgent(router)
    result = agent.execute(make_task())

    assert result["agent_id"] == "backend"
    assert result["summary"] == "Backend implementation prepared."

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


def test_agent_proposes_changes_without_writing(tmp_path):
    projects_root = tmp_path / "projects"
    project = projects_root / "demo"
    project.mkdir(parents=True)

    router = MagicMock()
    router.select_model.return_value = "cloud_coding"
    router.chat.return_value = json.dumps({
        "summary": "Created a starter module.",
        "file_changes": [
            {
                "path": "src/main.py",
                "operation": "create",
                "content": "print('Hello Forge')",
            }
        ],
    })

    agent = ArchitectAgent(
        router,
        projects_root=projects_root,
    )

    task = {
        **make_task(),
        "project_id": "demo",
    }

    result = agent.execute(task)

    assert len(result["proposed_changes"]) == 1
    assert result["changed_files"] == []
    assert not (project / "src" / "main.py").exists()

def test_direct_agent_writes_are_rejected(tmp_path):
    router = MagicMock()

    with pytest.raises(ValueError, match="Direct agent writes are disabled"):
        ArchitectAgent(
            router,
            projects_root=tmp_path,
            allow_file_writes=True,
        )
