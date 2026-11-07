
import json
import sqlite3
import uuid

from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from forge.core.workspace import ProjectWorkspace


class FileChangeProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str = Field(min_length=1)
    operation: Literal["create", "update"]
    content: str


class ApprovalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    approval_id: str
    project_id: str
    task_id: str
    agent_id: str
    summary: str
    changes: list[FileChangeProposal]
    status: Literal["pending", "approved", "rejected", "applied"]
    created_at: str
    decided_at: str | None = None
    applied_at: str | None = None


class ApprovalStore:
    """Persistent human approval queue for proposed project changes."""

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self):
        connection = sqlite3.connect(self.db_path, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self):
        with self._connect() as connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS forge_approvals (
                    approval_id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    task_id TEXT NOT NULL,
                    agent_id TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    changes_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    decided_at TEXT,
                    applied_at TEXT
                )
            """)

    @staticmethod
    def _from_row(row: sqlite3.Row) -> ApprovalRequest:
        return ApprovalRequest(
            approval_id=row["approval_id"],
            project_id=row["project_id"],
            task_id=row["task_id"],
            agent_id=row["agent_id"],
            summary=row["summary"],
            changes=json.loads(row["changes_json"]),
            status=row["status"],
            created_at=row["created_at"],
            decided_at=row["decided_at"],
            applied_at=row["applied_at"],
        )

    def create_request(
        self,
        project_id: str,
        task_id: str,
        agent_id: str,
        summary: str,
        changes: list[dict],
    ) -> ApprovalRequest:
        if not all(
            isinstance(value, str) and value.strip()
            for value in (project_id, task_id, agent_id, summary)
        ):
            raise ValueError("Approval metadata must not be empty.")

        validated_changes = [
            FileChangeProposal.model_validate(change)
            for change in changes
        ]

        if not validated_changes:
            raise ValueError("Approval request must contain file changes.")

        paths = [change.path for change in validated_changes]

        if len(paths) != len(set(paths)):
            raise ValueError("Approval request contains duplicate paths.")

        request = ApprovalRequest(
            approval_id=str(uuid.uuid4()),
            project_id=project_id,
            task_id=task_id,
            agent_id=agent_id,
            summary=summary,
            changes=validated_changes,
            status="pending",
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO forge_approvals (
                    approval_id, project_id, task_id, agent_id,
                    summary, changes_json, status, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    request.approval_id,
                    request.project_id,
                    request.task_id,
                    request.agent_id,
                    request.summary,
                    json.dumps([
                        change.model_dump()
                        for change in request.changes
                    ]),
                    request.status,
                    request.created_at,
                ),
            )

        return request

    def get(self, approval_id: str) -> ApprovalRequest | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM forge_approvals WHERE approval_id = ?",
                (approval_id,),
            ).fetchone()

        return self._from_row(row) if row else None

    def list_pending(
        self,
        project_id: str | None = None,
    ) -> list[ApprovalRequest]:
        query = (
            "SELECT * FROM forge_approvals WHERE status = 'pending'"
        )
        parameters = ()

        if project_id is not None:
            query += " AND project_id = ?"
            parameters = (project_id,)

        query += " ORDER BY created_at"

        with self._connect() as connection:
            rows = connection.execute(query, parameters).fetchall()

        return [self._from_row(row) for row in rows]

    def decide(
        self,
        approval_id: str,
        decision: Literal["approved", "rejected"],
    ) -> ApprovalRequest:
        if decision not in ("approved", "rejected"):
            raise ValueError("Decision must be approved or rejected.")

        decided_at = datetime.now(timezone.utc).isoformat()

        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE forge_approvals
                SET status = ?, decided_at = ?
                WHERE approval_id = ? AND status = 'pending'
                """,
                (decision, decided_at, approval_id),
            )

            if cursor.rowcount != 1:
                raise ValueError(
                    "Approval request does not exist or is no longer pending."
                )

        request = self.get(approval_id)

        if request is None:
            raise RuntimeError("Approval request disappeared.")

        return request

    def apply_approved(
        self,
        approval_id: str,
        workspace: ProjectWorkspace,
    ) -> ApprovalRequest:
        """Apply changes only after approval and revalidate every path."""

        request = self.get(approval_id)

        if request is None:
            raise ValueError("Approval request not found.")

        if request.status != "approved":
            raise ValueError("Only approved changes can be applied.")

        if workspace.project_id != request.project_id:
            raise ValueError("Approval belongs to a different project.")

        validated = []

        # Validate the entire change set before writing anything.
        for change in request.changes:
            path = workspace.validate_file_path(change.path)
            exists = path.exists()

            if change.operation == "create" and exists:
                raise ValueError(
                    f"Cannot create '{change.path}': file already exists."
                )

            if change.operation == "update" and not exists:
                raise ValueError(
                    f"Cannot update '{change.path}': file does not exist."
                )

            validated.append((change, path))

        for change, _ in validated:
            workspace.write_file(change.path, change.content)

        applied_at = datetime.now(timezone.utc).isoformat()

        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE forge_approvals
                SET status = 'applied', applied_at = ?
                WHERE approval_id = ? AND status = 'approved'
                """,
                (applied_at, approval_id),
            )

            if cursor.rowcount != 1:
                raise RuntimeError(
                    "Approval status changed during file application."
                )

        result = self.get(approval_id)

        if result is None:
            raise RuntimeError("Applied approval could not be retrieved.")

        return result
