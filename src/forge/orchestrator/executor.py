
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Mapping

from forge.agents.registry import AgentRegistry


AgentHandler = Callable[[dict[str, Any]], Any]


class AgentExecutor:
    def __init__(
        self,
        registry: AgentRegistry,
        handlers: Mapping[str, AgentHandler],
        max_parallel_agents: int = 3,
    ):
        if (
            not isinstance(max_parallel_agents, int)
            or isinstance(max_parallel_agents, bool)
            or max_parallel_agents < 1
        ):
            raise ValueError("max_parallel_agents must be a positive integer.")

        self.registry = registry
        self.handlers = dict(handlers)
        self.max_parallel_agents = max_parallel_agents

    def _execute_task(self, task: dict[str, Any]) -> dict[str, Any]:
        task_id = task.get("task_id", "unknown")
        agent_id = task.get("assigned_agent", "unknown")

        try:
            if not isinstance(agent_id, str) or not agent_id.strip():
                raise ValueError("Task has no valid assigned agent.")

            agent_config = self.registry.get(agent_id)

            if agent_config is None:
                raise ValueError(f"Agent '{agent_id}' is not registered.")

            if not agent_config.enabled:
                raise ValueError(f"Agent '{agent_id}' is disabled.")

            handler = self.handlers.get(agent_id)

            if handler is None:
                raise ValueError(
                    f"No execution handler registered for '{agent_id}'."
                )

            output = handler(task)

            return {
                "task_id": task_id,
                "assigned_agent": agent_id,
                "status": "completed",
                "output": output,
            }

        except Exception as error:
            return {
                "task_id": task_id,
                "assigned_agent": agent_id,
                "status": "failed",
                "error": f"{type(error).__name__}: {error}",
            }

    def execute_batches(
        self,
        batches: list[list[dict[str, Any]]],
    ) -> list[dict[str, Any]]:
        """Execute dependency-safe batches in order."""

        results = []
        execution_blocked = False

        for batch in batches:
            if execution_blocked:
                for task in batch:
                    results.append({
                        "task_id": task.get("task_id", "unknown"),
                        "assigned_agent": task.get(
                            "assigned_agent", "unknown"
                        ),
                        "status": "skipped",
                        "error": "Skipped because an earlier batch failed.",
                    })
                continue

            if len(batch) > self.max_parallel_agents:
                raise ValueError(
                    "Batch exceeds the maximum parallel-agent limit."
                )

            agent_ids = [
                task.get("assigned_agent")
                for task in batch
            ]

            if len(agent_ids) != len(set(agent_ids)):
                raise ValueError(
                    "An agent cannot receive multiple tasks in one batch."
                )

            with ThreadPoolExecutor(
                max_workers=self.max_parallel_agents
            ) as pool:
                batch_results = list(
                    pool.map(self._execute_task, batch)
                )

            results.extend(batch_results)

            if any(
                result["status"] == "failed"
                for result in batch_results
            ):
                execution_blocked = True

        return results
