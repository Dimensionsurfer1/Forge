
from collections.abc import Callable
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

from forge.core.approvals import ApprovalRequest, ApprovalStore
from forge.core.config import load_forge_config
from forge.core.workspace import ProjectWorkspace

from fastapi.middleware.cors import CORSMiddleware

class ApprovalDecision(BaseModel):
    decision: Literal["approved", "rejected"]


def create_app(
    approval_store: ApprovalStore,
    workspace_resolver: Callable[[str], ProjectWorkspace],
) -> FastAPI:
    app = FastAPI(
        title="Forge API",
        version="0.1.0",
        description="Forge approval management API",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.get("/approvals", response_model=list[ApprovalRequest])
    def list_approvals(project_id: str | None = Query(default=None)):
        return approval_store.list_pending(project_id)

    @app.get("/approvals/{approval_id}", response_model=ApprovalRequest)
    def get_approval(approval_id: str):
        request = approval_store.get(approval_id)

        if request is None:
            raise HTTPException(404, "Approval request not found.")

        return request

    @app.post(
        "/approvals/{approval_id}/decision",
        response_model=ApprovalRequest,
    )
    def decide_approval(approval_id: str, body: ApprovalDecision):
        if approval_store.get(approval_id) is None:
            raise HTTPException(404, "Approval request not found.")

        try:
            return approval_store.decide(approval_id, body.decision)
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc

    @app.post("/approvals/{approval_id}/apply",
              response_model=ApprovalRequest)
    def apply_approval(approval_id: str):
        request = approval_store.get(approval_id)

        if request is None:
            raise HTTPException(404, "Approval request not found.")

        try:
            workspace = workspace_resolver(request.project_id)
            return approval_store.apply_approved(approval_id, workspace)
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc

    return app


def create_configured_app() -> FastAPI:
    """Build the API using Forge's configured storage and projects."""

    config = load_forge_config()
    storage = config["storage"]

    approval_store = ApprovalStore(storage["database"])
    projects_root = Path(storage["projects"])

    def resolve_workspace(project_id: str) -> ProjectWorkspace:
        return ProjectWorkspace(
            projects_root=projects_root,
            project_id=project_id,
        )

    return create_app(approval_store, resolve_workspace)
