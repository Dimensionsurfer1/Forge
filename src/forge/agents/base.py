
import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from forge.core.workspace import ProjectWorkspace
from forge.model_router import ModelRouter


class ProposedFileChange(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str = Field(min_length=1)
    operation: Literal["create", "update"]
    content: str


class AgentWorkProduct(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str
    file_changes: list[ProposedFileChange] = Field(
        default_factory=list
    )


class SpecialistAgent:
    agent_id: str
    task_type: str
    system_prompt: str

    def __init__(
        self,
        router: ModelRouter,
        projects_root: str | Path | None = None,
        allow_file_writes: bool = False,
    ):
        self.router = router

        self.projects_root = (
            Path(projects_root).resolve()
            if projects_root is not None
            else None
        )

        if allow_file_writes:
            raise ValueError(
                "Direct agent writes are disabled. "
                "Use ApprovalStore to approve and apply changes."
            )

        self.allow_file_writes = False

    def _get_workspace_context(
        self,
        workspace: ProjectWorkspace,
    ) -> dict[str, str]:
        """Read a bounded snapshot of project text files."""

        supported_extensions = {
            ".py", ".md", ".yaml", ".yml", ".toml",
            ".json", ".ts", ".tsx", ".js", ".jsx",
            ".html", ".css", ".sql", ".txt",
        }

        snapshot: dict[str, str] = {}
        total_chars = 0

        for relative_path in workspace.list_files(max_files=100):
            if (
                Path(relative_path).suffix.lower()
                not in supported_extensions
            ):
                continue

            if len(snapshot) >= 20 or total_chars >= 20_000:
                break

            try:
                content = workspace.read_file(relative_path)
            except (UnicodeDecodeError, ValueError, OSError):
                continue

            content = content[:4_000]

            remaining = 20_000 - total_chars
            content = content[:remaining]

            if not content:
                continue

            snapshot[relative_path] = content
            total_chars += len(content)

        return snapshot

    def execute(
        self,
        task: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute a specialist task and return proposed changes."""

        task_id = task.get("task_id")
        description = task.get("description")

        if not isinstance(task_id, str) or not task_id.strip():
            raise ValueError("Task must have a valid task_id.")

        if not isinstance(description, str) or not description.strip():
            raise ValueError(
                f"Task '{task_id}' has no description."
            )

        project_id = task.get("project_id")
        workspace_context: dict[str, str] = {}

        # Load the assigned project's workspace.
        if self.projects_root is not None:
            if not isinstance(project_id, str) or not project_id.strip():
                raise ValueError(
                    "Task must identify its project."
                )

            workspace = ProjectWorkspace(
                projects_root=self.projects_root,
                project_id=project_id,
            )

            workspace_context = self._get_workspace_context(
                workspace
            )

        # Select the appropriate model.
        model_id = self.router.select_model(self.task_type)

        output_schema = json.dumps(
            AgentWorkProduct.model_json_schema(),
            indent=2,
        )

        messages = [
            {
                "role": "system",
                "content": (
                    f"{self.system_prompt}\n\n"
                    "You are working inside a managed project workspace.\n"
                    "Use the supplied project files as the source of truth.\n"
                    "Return ONLY valid JSON matching this schema:\n"
                    f"{output_schema}\n"
                    "For every proposed file change, provide:\n"
                    "- Relative file path\n"
                    "- Operation: create or update\n"
                    "- Complete file content\n\n"
                    "Do not use absolute paths or paths containing '..'.\n"
                    "Do not claim that files were modified.\n"
                    "Your changes are proposals and require human approval."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "task": task,
                        "project_files": workspace_context,
                    },
                    indent=2,
                ),
            },
        ]

        response = self.router.chat(
            messages=messages,
            model=model_id,
            max_tokens=6000,
        )

        # Validate the model's response.
        try:
            work_product = AgentWorkProduct.model_validate_json(
                response
            )
        except Exception as error:
            raise ValueError(
                f"Agent '{self.agent_id}' returned an invalid "
                "work product."
            ) from error

        proposed_changes = [
            change.model_dump()
            for change in work_product.file_changes
        ]

        # Reject duplicate paths.
        paths = [
            change["path"]
            for change in proposed_changes
        ]

        if len(paths) != len(set(paths)):
            raise ValueError(
                "Agent returned duplicate file paths."
            )

        # File changes require an assigned project workspace.
        if proposed_changes and self.projects_root is None:
            raise ValueError(
                "File changes require an assigned project workspace."
            )

        # Validate every proposed operation.
        # No files are written here.
        if self.projects_root is not None:
            workspace = ProjectWorkspace(
                projects_root=self.projects_root,
                project_id=project_id,
            )

            for change in proposed_changes:
                path = change["path"]

                target = workspace.validate_file_path(path)
                exists = target.exists()

                if change["operation"] == "create" and exists:
                    raise ValueError(
                        f"Cannot create '{path}': "
                        "file already exists."
                    )

                if change["operation"] == "update" and not exists:
                    raise ValueError(
                        f"Cannot update '{path}': "
                        "file does not exist."
                    )

        # Agents never apply changes directly.
        changed_files: list[str] = []

        return {
            "task_id": task_id,
            "agent_id": self.agent_id,
            "model": model_id,
            "summary": work_product.summary,
            "proposed_changes": proposed_changes,
            "changed_files": changed_files,
        }
