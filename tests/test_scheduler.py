
import pytest

from forge.orchestrator.scheduler import build_execution_batches


def sample_tasks():
    return [
        {
            "task_id": "T1",
            "description": "Design architecture.",
            "assigned_agent": "architect",
            "dependencies": [],
            "priority": "high",
            "status": "pending",
        },
        {
            "task_id": "T2",
            "description": "Build backend.",
            "assigned_agent": "backend",
            "dependencies": ["T1"],
            "priority": "medium",
            "status": "pending",
        },
        {
            "task_id": "T3",
            "description": "Build frontend.",
            "assigned_agent": "frontend",
            "dependencies": ["T1"],
            "priority": "medium",
            "status": "pending",
        },
        {
            "task_id": "T4",
            "description": "Test the application.",
            "assigned_agent": "qa",
            "dependencies": ["T2", "T3"],
            "priority": "high",
            "status": "pending",
        },
    ]


def test_dependencies_create_separate_batches():
    batches = build_execution_batches(sample_tasks())

    assert len(batches) == 3
    assert [task["task_id"] for task in batches[0]] == ["T1"]
    assert {task["task_id"] for task in batches[1]} == {"T2", "T3"}
    assert [task["task_id"] for task in batches[2]] == ["T4"]


def test_independent_tasks_run_in_parallel():
    tasks = sample_tasks()[:3]
    batches = build_execution_batches(tasks)

    assert len(batches) == 2
    assert len(batches[0]) == 1
    assert len(batches[1]) == 2


def test_parallel_limit_is_respected():
    tasks = [
        {
            "task_id": f"T{i}",
            "description": f"Task {i}",
            "assigned_agent": f"agent_{i}",
            "dependencies": [],
            "priority": "medium",
            "status": "pending",
        }
        for i in range(1, 5)
    ]

    batches = build_execution_batches(
        tasks,
        max_parallel_agents=2,
    )

    assert [len(batch) for batch in batches] == [2, 2]


def test_unknown_dependency_is_rejected():
    tasks = sample_tasks()
    tasks[1]["dependencies"] = ["T99"]

    with pytest.raises(ValueError, match="unknown dependencies"):
        build_execution_batches(tasks)


def test_circular_dependencies_are_rejected():
    tasks = sample_tasks()
    tasks[0]["dependencies"] = ["T4"]

    with pytest.raises(ValueError, match="Circular"):
        build_execution_batches(tasks)
