
import json
from unittest.mock import MagicMock

from forge.core.state import create_workflow_state
from forge.orchestrator.workflow import build_workflow


def test_workflow_calls_planner():
    router = MagicMock()

    router.select_model.return_value = "local_qwen"
    router.chat.return_value = json.dumps({
        "summary": "Build a MUN committee management system.",
        "tasks": [
            {
                "task_id": "T1",
                "description": "Design the system architecture.",
                "assigned_agent": "architect",
                "dependencies": [],
                "priority": "high",
                "status": "pending",
            },
            {
                "task_id": "T2",
                "description": "Implement the backend APIs.",
                "assigned_agent": "backend",
                "dependencies": ["T1"],
                "priority": "high",
                "status": "pending",
            },
        ],
    })

    workflow = build_workflow(router)

    initial_state = create_workflow_state(
        project_id="politag-mun-engine",
        workflow_id="test-workflow-001",
        task_request="Build a basic MUN committee management system.",
    )

    result = workflow.invoke(initial_state)

    assert result["status"] == "planned"
    assert len(result["tasks"]) == 2
    assert result["tasks"][0]["assigned_agent"] == "architect"
    assert result["tasks"][1]["dependencies"] == ["T1"]

    router.chat.assert_called_once()
