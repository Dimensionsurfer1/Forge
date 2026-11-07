from operator import add
import operator
from typing import Annotated, Any, Literal
from typing_extensions import TypedDict

from pydantic import BaseModel, ConfigDict, Field


class TaskRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: str
    title: str
    assigned_agent: str | None = None
    status: Literal[
        "pending", "assigned", "in_progress",
        "completed", "failed", "blocked"
    ] = "pending"
    dependencies: list[str] = Field(default_factory=list)
    result: str | None = None
    blocker: str | None = None


class AgentHandover(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agent_id: str
    task_id: str
    work_completed: list[str] = Field(default_factory=list)
    files_changed: list[str] = Field(default_factory=list)
    decisions: list[str] = Field(default_factory=list)
    pending_work: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)


class WorkflowState(TypedDict):
    project_id: str
    workflow_id: str
    task_request: str
    status: Literal["pending", "running", "paused", "completed", "failed"]
    tasks: dict[str, TaskRecord]
    agent_outputs: dict[str, Any]
    handovers: Annotated[list[AgentHandover], add]
    errors: Annotated[list[str], add]
    events: Annotated[list[str], add]
    pending_approvals: list[str]
    approval_ids: Annotated[list[str], operator.add]

    execution_results: Annotated[
        list[dict[str, Any]],
        operator.add,
    ]

    execution_batches: Annotated[
        list[list[dict[str, Any]]],
        operator.add,
    ]

def create_workflow_state(
    project_id: str,
    workflow_id: str,
    task_request: str,
) -> WorkflowState:
    return {
        "project_id": project_id,
        "workflow_id": workflow_id,
        "task_request": task_request,
        "status": "pending",
        "tasks": {},
        "agent_outputs": {},
        "handovers": [],
        "errors": [],
        "events": [],
        "pending_approvals": [],
        "execution_batches": [],
        "execution_results": [],
        "approval_ids": [],
    }
