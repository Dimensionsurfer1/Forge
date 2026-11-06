
import json
from types import SimpleNamespace
from unittest.mock import MagicMock

from forge.core.state import create_workflow_state
from forge.orchestrator.executor import AgentExecutor
from forge.orchestrator.workflow import build_workflow


def test_workflow_plans_schedules_and_executes():
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

    registry = MagicMock()
    registry.get.return_value = SimpleNamespace(enabled=True)

    executor = AgentExecutor(
        registry=registry,
        handlers={
            "architect": lambda task: "Mock architecture completed.",
            "backend": lambda task: "Mock backend completed.",
        },
        max_parallel_agents=3,
    )

    workflow = build_workflow(
        router,
        executor=executor,
        max_parallel_agents=3,
    )

    initial_state = create_workflow_state(
        project_id="politag-mun-engine",
        workflow_id="test-workflow-001",
        task_request="Build a basic MUN committee management system.",
    )

    result = workflow.invoke(initial_state)

    assert result["status"] == "completed"

    assert len(result["tasks"]) == 2
    assert len(result["execution_batches"]) == 2
    assert len(result["execution_results"]) == 2

    assert all(
        item["status"] == "completed"
        for item in result["execution_results"]
    )

    assert result["execution_results"][0]["output"] == (
        "Mock architecture completed."
    )

    router.chat.assert_called_once()


def test_workflow_automatically_builds_specialist_agents():
    from types import SimpleNamespace

    router = MagicMock()

    router.select_model.side_effect = [
        "local_qwen",
        "cloud_coding",
        "cloud_coding",
    ]

    router.chat.side_effect = [
        json.dumps({
            "summary": "Build a MUN management system.",
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
        }),
        json.dumps({
            "summary": "Architecture design completed.",
            "file_changes": [],
        }),
        json.dumps({
            "summary": "Backend implementation prepared.",
            "file_changes": [],
        }),
    ]

    registry = MagicMock()
    registry.get.return_value = SimpleNamespace(enabled=True)

    workflow = build_workflow(
        router,
        registry=registry,
        max_parallel_agents=3,
    )

    initial_state = create_workflow_state(
        project_id="politag-mun-engine",
        workflow_id="real-agent-test-001",
        task_request="Build a MUN committee management system.",
    )

    result = workflow.invoke(initial_state)

    assert result["status"] == "completed"
    assert len(result["execution_results"]) == 2

    assert result["execution_results"][0]["assigned_agent"] == "architect"
    assert result["execution_results"][1]["assigned_agent"] == "backend"

    assert result["execution_results"][0]["output"]["summary"] == (
        "Architecture design completed."
    )

    assert result["execution_results"][1]["output"]["summary"] == (
        "Backend implementation prepared."
    )

    assert router.chat.call_count == 3

