
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from forge.core.state import WorkflowState
from forge.model_router import ModelRouter


class PlannedTask(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: str = Field(min_length=1)
    description: str = Field(min_length=1)
    assigned_agent: Literal[
        "architect",
        "frontend",
        "backend",
        "audio",
        "qa",
        "reviewer",
        "integrator",
    ]
    dependencies: list[str] = Field(default_factory=list)
    priority: Literal["low", "medium", "high", "critical"] = "medium"
    status: Literal["pending"] = "pending"


class TaskPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str
    tasks: list[PlannedTask] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_dependencies(self):
        task_ids = [task.task_id for task in self.tasks]

        if len(task_ids) != len(set(task_ids)):
            raise ValueError("Task IDs must be unique.")

        known_ids = set(task_ids)

        for task in self.tasks:
            if task.task_id in task.dependencies:
                raise ValueError(
                    f"Task '{task.task_id}' cannot depend on itself."
                )

            unknown = set(task.dependencies) - known_ids
            if unknown:
                raise ValueError(
                    f"Task '{task.task_id}' has unknown dependencies: "
                    f"{sorted(unknown)}"
                )

        # Detect circular dependencies.
        graph = {
            task.task_id: task.dependencies
            for task in self.tasks
        }
        visiting = set()
        visited = set()

        def visit(task_id: str):
            if task_id in visiting:
                raise ValueError("Circular task dependencies detected.")

            if task_id in visited:
                return

            visiting.add(task_id)

            for dependency in graph[task_id]:
                visit(dependency)

            visiting.remove(task_id)
            visited.add(task_id)

        for task_id in graph:
            visit(task_id)

        return self


def parse_task_plan(response: str) -> TaskPlan:
    """Parse and validate the Planner's JSON response."""
    try:
        data = json.loads(response)
    except json.JSONDecodeError as error:
        raise ValueError(
            "Planner did not return valid JSON."
        ) from error

    return TaskPlan.model_validate(data)


def create_plan(state: WorkflowState, router: ModelRouter) -> dict:
    """Generate a structured development plan."""

    model_id = router.select_model("simple_tasks")

    schema = json.dumps(TaskPlan.model_json_schema(), indent=2)

    messages = [
        {
            "role": "system",
            "content": f"""
You are Forge's Planner.

Break the user's software request into small,
clear development tasks.

Return ONLY valid JSON. Do not use Markdown fences.

Follow this JSON schema exactly:
{schema}

Available agents and their roles:
- architect: system design and technical decisions
- frontend: user interface and frontend development
- backend: APIs, databases and server logic
- audio: audio processing, recording and transcription
- qa: testing and quality assurance
- reviewer: code and security review
- integrator: integration and Git operations

Rules:
- Assign each task to one appropriate agent.
- Use unique task IDs such as T1, T2 and T3.
- Add dependencies only when a task genuinely needs another task first.
- Use an empty dependency list when tasks are independent.
- Do not invent agents.
- Every task must have status "pending".
- Use priorities: low, medium, high or critical.
""",
        },
        {
            "role": "user",
            "content": state["task_request"],
        },
    ]

    response = router.chat(
        messages=messages,
        model=model_id,
        max_tokens=4000,
    )

    plan = parse_task_plan(response)

    return {
        "status": "planned",
        "tasks": [
            task.model_dump()
            for task in plan.tasks
        ],
        "agent_outputs": {
            "planner": {
                "summary": plan.summary,
                "task_count": len(plan.tasks),
                "model": model_id,
            }
        },
        "events": [
            f"Planner selected model: {model_id}",
            f"Planner generated {len(plan.tasks)} tasks.",
            "Task plan passed validation.",
        ],
    }
