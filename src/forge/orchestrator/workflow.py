
from pathlib import Path
from typing import Any

import yaml
from langgraph.graph import END, START, StateGraph

from forge.core.state import WorkflowState
from forge.model_router import ModelRouter
from forge.orchestrator.planner import create_plan
from forge.orchestrator.scheduler import build_execution_batches


def initialize_workflow(state: WorkflowState) -> dict:
    """Initialize a workflow and record its start."""
    return {
        "status": "running",
        "events": [
            f"Workflow started for project: {state['project_id']}"
        ],
    }


def load_parallel_limit() -> int:
    """Read the parallel-agent limit from Forge configuration."""
    project_root = Path(__file__).resolve().parents[3]
    config_path = project_root / "config" / "forge.yaml"

    with config_path.open("r", encoding="utf-8") as file:
        config: dict[str, Any] = yaml.safe_load(file) or {}

    limit = config.get("execution", {}).get(
        "max_parallel_agents", 3
    )

    if not isinstance(limit, int) or isinstance(limit, bool) or limit < 1:
        raise ValueError(
            "execution.max_parallel_agents must be a positive integer."
        )

    return limit


def build_workflow(
    router: ModelRouter | None = None,
    max_parallel_agents: int | None = None,
):
    """Build the planning and scheduling workflow."""

    model_router = router or ModelRouter()

    parallel_limit = (
        max_parallel_agents
        if max_parallel_agents is not None
        else load_parallel_limit()
    )

    if parallel_limit < 1:
        raise ValueError("max_parallel_agents must be at least 1.")

    graph = StateGraph(WorkflowState)

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

    graph.add_node("scheduler", schedule_tasks)

    graph.add_edge(START, "initialize")
    graph.add_edge("initialize", "planner")
    graph.add_edge("planner", "scheduler")
    graph.add_edge("scheduler", END)

    return graph.compile()
