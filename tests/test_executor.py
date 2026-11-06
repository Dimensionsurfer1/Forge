
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from forge.orchestrator.executor import AgentExecutor


def make_registry(enabled=True):
    registry = MagicMock()
    registry.get.return_value = SimpleNamespace(enabled=enabled)
    return registry


def make_task(task_id, agent_id):
    return {
        "task_id": task_id,
        "assigned_agent": agent_id,
        "description": f"Test task {task_id}",
    }


def test_executor_runs_independent_tasks():
    registry = make_registry()

    executor = AgentExecutor(
        registry=registry,
        handlers={
            "architect": lambda task: "Architecture completed",
            "backend": lambda task: "Backend completed",
        },
        max_parallel_agents=2,
    )

    results = executor.execute_batches([
        [
            make_task("T1", "architect"),
            make_task("T2", "backend"),
        ]
    ])

    assert len(results) == 2
    assert all(r["status"] == "completed" for r in results)


def test_failed_task_blocks_later_batches():
    registry = make_registry()

    def failing_handler(task):
        raise RuntimeError("Agent execution failed")

    executor = AgentExecutor(
        registry=registry,
        handlers={
            "architect": lambda task: "Done",
            "backend": failing_handler,
            "qa": lambda task: "Tests completed",
        },
    )

    results = executor.execute_batches([
        [make_task("T1", "architect")],
        [make_task("T2", "backend")],
        [make_task("T3", "qa")],
    ])

    assert results[0]["status"] == "completed"
    assert results[1]["status"] == "failed"
    assert results[2]["status"] == "skipped"


def test_unregistered_agent_fails():
    registry = make_registry()
    registry.get.return_value = None

    executor = AgentExecutor(
        registry=registry,
        handlers={"architect": lambda task: "Done"},
    )

    results = executor.execute_batches([
        [make_task("T1", "unknown")]
    ])

    assert results[0]["status"] == "failed"
    assert "not registered" in results[0]["error"]


def test_disabled_agent_fails():
    executor = AgentExecutor(
        registry=make_registry(enabled=False),
        handlers={"architect": lambda task: "Done"},
    )

    results = executor.execute_batches([
        [make_task("T1", "architect")]
    ])

    assert results[0]["status"] == "failed"
    assert "disabled" in results[0]["error"]


def test_parallel_limit_is_enforced():
    executor = AgentExecutor(
        registry=make_registry(),
        handlers={
            "architect": lambda task: "Done",
            "backend": lambda task: "Done",
        },
        max_parallel_agents=1,
    )

    with pytest.raises(ValueError, match="parallel-agent limit"):
        executor.execute_batches([
            [
                make_task("T1", "architect"),
                make_task("T2", "backend"),
            ]
        ])


def test_same_agent_cannot_receive_two_parallel_tasks():
    executor = AgentExecutor(
        registry=make_registry(),
        handlers={"backend": lambda task: "Done"},
    )

    with pytest.raises(ValueError, match="multiple tasks"):
        executor.execute_batches([
            [
                make_task("T1", "backend"),
                make_task("T2", "backend"),
            ]
        ])
