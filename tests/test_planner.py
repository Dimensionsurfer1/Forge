
import pytest

from forge.orchestrator.planner import TaskPlan, parse_task_plan


def valid_plan():
    return {
        "summary": "Build a web application.",
        "tasks": [
            {
                "task_id": "T1",
                "description": "Design the architecture.",
                "assigned_agent": "architect",
                "dependencies": [],
                "priority": "high",
                "status": "pending",
            },
            {
                "task_id": "T2",
                "description": "Build the backend.",
                "assigned_agent": "backend",
                "dependencies": ["T1"],
                "priority": "medium",
                "status": "pending",
            },
        ],
    }


def test_valid_plan_is_accepted():
    plan = TaskPlan.model_validate(valid_plan())

    assert len(plan.tasks) == 2
    assert plan.tasks[1].dependencies == ["T1"]


def test_unknown_dependency_is_rejected():
    data = valid_plan()
    data["tasks"][1]["dependencies"] = ["T99"]

    with pytest.raises(ValueError):
        TaskPlan.model_validate(data)


def test_circular_dependencies_are_rejected():
    data = valid_plan()
    data["tasks"][0]["dependencies"] = ["T2"]

    with pytest.raises(ValueError):
        TaskPlan.model_validate(data)


def test_invalid_json_is_rejected():
    with pytest.raises(ValueError, match="valid JSON"):
        parse_task_plan("This is not JSON.")
