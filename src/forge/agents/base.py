
from abc import ABC
from typing import Any

from forge.model_router import ModelRouter


class SpecialistAgent(ABC):
    agent_id: str
    task_type: str
    system_prompt: str

    def __init__(self, router: ModelRouter):
        self.router = router

    def execute(self, task: dict[str, Any]) -> dict[str, Any]:
        task_id = task.get("task_id")
        description = task.get("description")

        if not isinstance(task_id, str) or not task_id.strip():
            raise ValueError("Task must have a valid task_id.")

        if not isinstance(description, str) or not description.strip():
            raise ValueError(f"Task '{task_id}' has no description.")

        model_id = self.router.select_model(self.task_type)

        messages = [
            {
                "role": "system",
                "content": self.system_prompt,
            },
            {
                "role": "user",
                "content": (
                    f"Task ID: {task_id}\n"
                    f"Task description: {description}\n"
                    f"Priority: {task.get('priority', 'medium')}\n"
                    f"Dependencies: {task.get('dependencies', [])}"
                ),
            },
        ]

        response = self.router.chat(
            messages=messages,
            model=model_id,
            max_tokens=4000,
        )

        return {
            "task_id": task_id,
            "agent_id": self.agent_id,
            "model": model_id,
            "content": response,
        }

