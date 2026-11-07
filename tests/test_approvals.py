
import pytest

from forge.core.approvals import ApprovalStore
from forge.core.workspace import ProjectWorkspace


@pytest.fixture
def setup_approval(tmp_path):
    projects_root = tmp_path / "projects"
    project = projects_root / "demo"
    project.mkdir(parents=True)

    workspace = ProjectWorkspace(
        projects_root=projects_root,
        project_id="demo",
    )

    store = ApprovalStore(tmp_path / "approvals.db")

    changes = [
        {
            "path": "src/main.py",
            "operation": "create",
            "content": "print('Hello Forge')",
        }
    ]

    request = store.create_request(
        project_id="demo",
        task_id="T1",
        agent_id="backend",
        summary="Create the application entry point.",
        changes=changes,
    )

    return store, workspace, request, project


def test_new_approval_starts_pending(setup_approval):
    store, _, request, _ = setup_approval

    assert request.status == "pending"
    assert store.get(request.approval_id).status == "pending"


def test_pending_changes_cannot_be_applied(setup_approval):
    store, workspace, request, project = setup_approval

    with pytest.raises(ValueError, match="Only approved"):
        store.apply_approved(request.approval_id, workspace)

    assert not (project / "src" / "main.py").exists()


def test_approved_changes_can_be_applied(setup_approval):
    store, workspace, request, project = setup_approval

    store.decide(request.approval_id, "approved")

    applied = store.apply_approved(
        request.approval_id,
        workspace,
    )

    assert applied.status == "applied"
    assert (project / "src" / "main.py").read_text(
        encoding="utf-8"
    ) == "print('Hello Forge')"


def test_rejected_changes_cannot_be_applied(setup_approval):
    store, workspace, request, project = setup_approval

    store.decide(request.approval_id, "rejected")

    with pytest.raises(ValueError, match="Only approved"):
        store.apply_approved(request.approval_id, workspace)

    assert not (project / "src" / "main.py").exists()


def test_approval_cannot_be_applied_to_another_project(
    setup_approval,
    tmp_path,
):
    store, _, request, _ = setup_approval

    other_root = tmp_path / "other-projects"
    other_project = other_root / "other"
    other_project.mkdir(parents=True)

    other_workspace = ProjectWorkspace(
        projects_root=other_root,
        project_id="other",
    )

    store.decide(request.approval_id, "approved")

    with pytest.raises(ValueError, match="different project"):
        store.apply_approved(
            request.approval_id,
            other_workspace,
        )


def test_invalid_create_operation_is_rejected(
    setup_approval,
):
    store, workspace, request, project = setup_approval

    store.decide(request.approval_id, "approved")

    (project / "src").mkdir()
    (project / "src" / "main.py").write_text(
        "Existing file",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="already exists"):
        store.apply_approved(request.approval_id, workspace)

def test_invalid_change_prevents_entire_batch(setup_approval):
    store, workspace, request, project = setup_approval

    batch = store.create_request(
        project_id="demo",
        task_id="T2",
        agent_id="backend",
        summary="Create two files.",
        changes=[
            {
                "path": "src/first.py",
                "operation": "create",
                "content": "print('First')",
            },
            {
                "path": "src/missing.py",
                "operation": "update",
                "content": "print('Second')",
            },
        ],
    )

    store.decide(batch.approval_id, "approved")

    with pytest.raises(ValueError, match="does not exist"):
        store.apply_approved(batch.approval_id, workspace)

    assert not (project / "src" / "first.py").exists()
    assert batch.status == "pending" or store.get(
        batch.approval_id
    ).status == "approved"