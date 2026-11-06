
from langgraph.graph import END, START, StateGraph

from forge.core.state import WorkflowState
from forge.model_router import ModelRouter
from forge.orchestrator.planner import create_plan


def initialize_workflow(state: WorkflowState) -> dict:
    return {
        "status": "running",
        "events": [
            f"Workflow started for project: {state['project_id']}"
        ],
    }


def build_workflow(router: ModelRouter | None = None):
    model_router = router or ModelRouter()

    graph = StateGraph(WorkflowState)

    graph.add_node("initialize", initialize_workflow)
    graph.add_node(
        "planner",
        lambda state: create_plan(state, model_router),
    )

    graph.add_edge(START, "initialize")
    graph.add_edge("initialize", "planner")
    graph.add_edge("planner", END)

    return graph.compile()
