from langgraph.graph import END, START, StateGraph

from forge.core.state import WorkflowState


def initialize_workflow(state: WorkflowState) -> dict:
    """Initialize a workflow and record its start."""
    return {
        "status": "running",
        "events": [
            f"Workflow started for project: {state['project_id']}"
        ],
    }


def planner_checkpoint(state: WorkflowState) -> dict:
    """Temporary checkpoint until the AI Planner is connected."""
    return {
        "status": "paused",
        "events": [
            f"Task received by Planner stage: {state['task_request']}",
            "Planner is waiting for AI model integration.",
        ],
    }


def build_workflow():
    graph = StateGraph(WorkflowState)

    graph.add_node("initialize", initialize_workflow)
    graph.add_node("planner", planner_checkpoint)

    graph.add_edge(START, "initialize")
    graph.add_edge("initialize", "planner")
    graph.add_edge("planner", END)

    return graph.compile()
