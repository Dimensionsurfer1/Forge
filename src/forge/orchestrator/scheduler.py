
from typing import Any


PRIORITY_ORDER = {
    "critical": 0,
    "high": 1,
    "medium": 2,
    "low": 3,
}


def build_execution_batches(
    tasks: list[dict[str, Any]],
    max_parallel_agents: int = 3,
) -> list[list[dict[str, Any]]]:
    """Group tasks into dependency-safe execution batches."""

    if max_parallel_agents < 1:
        raise ValueError("max_parallel_agents must be at least 1.")

    task_by_id = {}

    for task in tasks:
        task_id = task.get("task_id")
        agent = task.get("assigned_agent")
        dependencies = task.get("dependencies", [])
        priority = task.get("priority", "medium")

        if not isinstance(task_id, str) or not task_id.strip():
            raise ValueError("Every task must have a valid task_id.")

        if task_id in task_by_id:
            raise ValueError(f"Duplicate task ID: {task_id}")

        if not isinstance(agent, str) or not agent.strip():
            raise ValueError(f"Task '{task_id}' has no assigned agent.")

        if not isinstance(dependencies, list):
            raise ValueError(
                f"Task '{task_id}' dependencies must be a list."
            )

        if not all(isinstance(dep, str) for dep in dependencies):
            raise ValueError(
                f"Task '{task_id}' has an invalid dependency."
            )

        if priority not in PRIORITY_ORDER:
            raise ValueError(
                f"Task '{task_id}' has invalid priority: {priority}"
            )

        if task_id in dependencies:
            raise ValueError(
                f"Task '{task_id}' cannot depend on itself."
            )

        task_by_id[task_id] = task

    known_ids = set(task_by_id)

    for task_id, task in task_by_id.items():
        unknown = set(task.get("dependencies", [])) - known_ids

        if unknown:
            raise ValueError(
                f"Task '{task_id}' has unknown dependencies: "
                f"{sorted(unknown)}"
            )

    remaining = set(task_by_id)
    completed = set()
    batches = []

    while remaining:
        ready = [
            task_by_id[task_id]
            for task_id in remaining
            if set(task_by_id[task_id].get("dependencies", []))
            .issubset(completed)
        ]

        if not ready:
            raise ValueError("Circular task dependencies detected.")

        ready.sort(
            key=lambda task: PRIORITY_ORDER[
                task.get("priority", "medium")
            ]
        )

        batch = []
        active_agents = set()

        for task in ready:
            agent = task["assigned_agent"]

            if agent in active_agents:
                continue

            batch.append(task.copy())
            active_agents.add(agent)

            if len(batch) >= max_parallel_agents:
                break

        if not batch:
            raise RuntimeError("Scheduler could not create an execution batch.")

        batches.append(batch)

        for task in batch:
            task_id = task["task_id"]
            remaining.remove(task_id)
            completed.add(task_id)

    return batches
