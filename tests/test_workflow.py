
import json
from unittest.mock import MagicMock

from forge.core.state import create_workflow_state
from forge.orchestrator.workflow import build_workflow


def test_workflow_calls_planner_and_scheduler():
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

    workflow = build_workflow(
        router,
        max_parallel_agents=3,
    )

    initial_state = create_workflow_state(
        project_id="politag-mun-engine",
        workflow_id="test-workflow-001",
        task_request="Build a basic MUN committee management system.",
    )

    result = workflow.invoke(initial_state)

    assert result["status"] == "scheduled"
    assert len(result["tasks"]) == 2
    assert len(result["execution_batches"]) == 2

    first_batch = result["execution_batches"][0]
    second_batch = result["execution_batches"][1]

    assert first_batch[0]["task_id"] == "T1"
    assert second_batch[0]["task_id"] == "T2"

    router.chat.assert_called_once()
