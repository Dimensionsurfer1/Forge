
from forge.core.state import WorkflowState
from forge.model_router import ModelRouter


def create_plan(state: WorkflowState, router: ModelRouter) -> dict:
    """Generate a task plan using the configured model."""

    model_id = router.select_model("simple_tasks")

    messages = [
        {
            "role": "system",
            "content": (
                "You are Forge's Planner. "
                "Break the user's software request into clear, "
                "small, ordered development tasks. "
                "Return a numbered task list. "
                "Do not write code."
            ),
        },
        {
            "role": "user",
            "content": state["task_request"],
        },
    ]

    plan = router.chat(
        messages=messages,
        model=model_id,
    )

    return {
        "status": "planned",
        "agent_outputs": {
            "planner": plan,
        },
        "events": [
            f"Planner selected model: {model_id}",
            "Planner successfully generated a task plan.",
        ],
    }
