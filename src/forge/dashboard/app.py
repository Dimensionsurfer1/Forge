
from collections.abc import Callable

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from typing import Literal

from forge.core.approvals import ApprovalRequest, ApprovalStore
from forge.core.workspace import ProjectWorkspace


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

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.get("/approvals", response_model=list[ApprovalRequest])
    def list_approvals(
        project_id: str | None = Query(default=None),
    ):
        return approval_store.list_pending(project_id)

    @app.get(
        "/approvals/{approval_id}",
        response_model=ApprovalRequest,
    )
    def get_approval(approval_id: str):
        request = approval_store.get(approval_id)

        if request is None:
            raise HTTPException(
                status_code=404,
                detail="Approval request not found.",
            )

        return request

    @app.post(
        "/approvals/{approval_id}/decision",
        response_model=ApprovalRequest,
    )
    def decide_approval(
        approval_id: str,
        body: ApprovalDecision,
    ):
        if approval_store.get(approval_id) is None:
            raise HTTPException(
                status_code=404,
                detail="Approval request not found.",
            )

        try:
            return approval_store.decide(
                approval_id,
                body.decision,
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=409,
                detail=str(exc),
            ) from exc

    @app.post(
        "/approvals/{approval_id}/apply",
        response_model=ApprovalRequest,
    )
    def apply_approval(approval_id: str):
        request = approval_store.get(approval_id)

        if request is None:
            raise HTTPException(
                status_code=404,
                detail="Approval request not found.",
            )

        try:
            workspace = workspace_resolver(request.project_id)
            return approval_store.apply_approved(
                approval_id,
                workspace,
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=409,
                detail=str(exc),
            ) from exc

    return app
