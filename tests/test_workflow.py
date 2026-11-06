
from unittest.mock import MagicMock

from forge.core.state import create_workflow_state
from forge.orchestrator.workflow import build_workflow


def test_workflow_calls_planner():
    router = MagicMock()

    router.select_model.return_value = "local_qwen"
    router.chat.return_value = (
        "1. Analyze requirements\n"
        "2. Design architecture\n"
        "3. Implement features\n"
        "4. Test the application"
    )

    workflow = build_workflow(router)

    initial_state = create_workflow_state(
        project_id="politag-mun-engine",
        workflow_id="test-workflow-001",
        task_request="Build a basic MUN committee management system.",
    )

    result = workflow.invoke(initial_state)

    assert result["status"] == "planned"
    assert "planner" in result["agent_outputs"]
    router.chat.assert_called_once()

