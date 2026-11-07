
from pathlib import Path
from typing import Any

import yaml
from langgraph.graph import END, START, StateGraph

from forge.agents.factory import build_agent_handlers
from forge.agents.registry import AgentRegistry
from forge.core.state import WorkflowState
from forge.core.approvals import ApprovalStore
from forge.model_router import ModelRouter
from forge.orchestrator.executor import AgentExecutor
from forge.orchestrator.planner import create_plan
from forge.orchestrator.scheduler import build_execution_batches
from forge.orchestrator.approval_queue import queue_proposed_changes


def initialize_workflow(state: WorkflowState) -> dict:
    return {
        "status": "running",
        "events": [
            f"Workflow started for project: {state['project_id']}"
        ],
    }


def load_parallel_limit() -> int:
    project_root = Path(__file__).resolve().parents[3]
    config_path = project_root / "config" / "forge.yaml"

    with config_path.open("r", encoding="utf-8") as file:
        config: dict[str, Any] = yaml.safe_load(file) or {}

    limit = config.get("execution", {}).get(
        "max_parallel_agents", 3
    )

    if (
        not isinstance(limit, int)
        or isinstance(limit, bool)
        or limit < 1
    ):
        raise ValueError(
            "execution.max_parallel_agents must be a positive integer."
        )

    return limit


def load_database_path() -> Path:
    """Load the SQLite database path from Forge configuration."""

    project_root = Path(__file__).resolve().parents[3]
    config_path = project_root / "config" / "forge.yaml"

    with config_path.open("r", encoding="utf-8") as file:
        config: dict[str, Any] = yaml.safe_load(file) or {}

    database = config.get("storage", {}).get(
        "database",
        "runtime/database/forge.db",
    )

    path = Path(database)

    if not path.is_absolute():
        path = project_root / path

    return path


def build_workflow(
    router: ModelRouter | None = None,
    *,
    executor: AgentExecutor | None = None,
    registry: AgentRegistry | None = None,
    projects_root: str | Path | None = None,
    allow_file_writes: bool = False,
    max_parallel_agents: int | None = None,
    approval_store: ApprovalStore | None = None,
):
    """Build the planning, scheduling and execution workflow."""

    model_router = router or ModelRouter()

    active_approval_store = (
        approval_store
        if approval_store is not None
        else ApprovalStore(load_database_path())
    )

    parallel_limit = (
        max_parallel_agents
        if max_parallel_agents is not None
        else load_parallel_limit()
    )

    if (
        not isinstance(parallel_limit, int)
        or isinstance(parallel_limit, bool)
        or parallel_limit < 1
    ):
        raise ValueError(
            "max_parallel_agents must be a positive integer."
        )

    if executor is None:
        project_root = Path(__file__).resolve().parents[3]

        workspace_root = (
            Path(projects_root)
            if projects_root is not None
            else project_root / "projects"
        )

        agent_registry = (
            registry if registry is not None else AgentRegistry()
        )

        executor = AgentExecutor(
            registry=agent_registry,
            handlers=build_agent_handlers(
                model_router,
                projects_root=workspace_root,
                allow_file_writes=allow_file_writes,
            ),
            max_parallel_agents=parallel_limit,
        )

    # Create the graph before registering nodes.
    graph = StateGraph(WorkflowState)

    def create_approval_requests(state: WorkflowState) -> dict:
        return queue_proposed_changes(
            state,
            active_approval_store,
        )

    graph.add_node("initialize", initialize_workflow)

    graph.add_node(
        "planner",
        lambda state: create_plan(state, model_router),
    )

    def schedule_tasks(state: WorkflowState) -> dict:
        batches = build_execution_batches(
            state["tasks"],
            max_parallel_agents=parallel_limit,
        )

        return {
            "execution_batches": batches,
            "status": "scheduled",
            "events": [
                f"Scheduler created {len(batches)} execution batches.",
                f"Parallel-agent limit: {parallel_limit}.",
            ],
        }

    def execute_tasks(state: WorkflowState) -> dict:
        execution_batches = [
            [
                {
                    **task,
                    "project_id": state["project_id"],
                }
                for task in batch
            ]
            for batch in state["execution_batches"]
        ]

        results = executor.execute_batches(execution_batches)

        failed = any(
            result["status"] == "failed"
            for result in results
        )

        completed = sum(
            result["status"] == "completed"
            for result in results
        )

        return {
            "execution_results": results,
            "status": "failed" if failed else "completed",
            "events": [
                f"Execution finished: {completed} tasks completed.",
                (
                    "One or more tasks failed."
                    if failed
                    else "All scheduled tasks completed."
                ),
            ],
        }

    graph.add_node("scheduler", schedule_tasks)
    graph.add_node("executor", execute_tasks)
    graph.add_node("approval_queue", create_approval_requests)

    graph.add_edge(START, "initialize")
    graph.add_edge("initialize", "planner")
    graph.add_edge("planner", "scheduler")
    graph.add_edge("scheduler", "executor")
    graph.add_edge("executor", "approval_queue")
    graph.add_edge("approval_queue", END)

    return graph.compile()
