
import pytest
from fastapi.testclient import TestClient

from forge.core.approvals import ApprovalStore
from forge.core.workspace import ProjectWorkspace
from forge.dashboard import create_app


@pytest.fixture
def setup_dashboard(tmp_path):
    projects_root = tmp_path / "projects"
    project = projects_root / "demo"
    project.mkdir(parents=True)

    workspace = ProjectWorkspace(projects_root, "demo")
    store = ApprovalStore(tmp_path / "approvals.db")

    request = store.create_request(
        project_id="demo",
        task_id="T1",
        agent_id="backend",
        summary="Create main.py",
        changes=[
            {
                "path": "main.py",
                "operation": "create",
                "content": "print('Hello Forge')",
            }
        ],
    )

    app = create_app(
        approval_store=store,
        workspace_resolver=lambda project_id: workspace,
    )

    return TestClient(app), store, request, project


def test_health_endpoint(setup_dashboard):
    client, _, _, _ = setup_dashboard

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_list_pending_approvals(setup_dashboard):
    client, _, request, _ = setup_dashboard

    response = client.get("/approvals")

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["approval_id"] == request.approval_id


def test_get_approval(setup_dashboard):
    client, _, request, _ = setup_dashboard

    response = client.get(f"/approvals/{request.approval_id}")

    assert response.status_code == 200
    assert response.json()["summary"] == "Create main.py"


def test_unknown_approval_returns_404(setup_dashboard):
    client, _, _, _ = setup_dashboard

    response = client.get("/approvals/unknown")

    assert response.status_code == 404


def test_approve_and_apply_changes(setup_dashboard):
    client, _, request, project = setup_dashboard

    decision = client.post(
        f"/approvals/{request.approval_id}/decision",
        json={"decision": "approved"},
    )

    assert decision.status_code == 200
    assert decision.json()["status"] == "approved"

    applied = client.post(
        f"/approvals/{request.approval_id}/apply"
    )

    assert applied.status_code == 200
    assert applied.json()["status"] == "applied"
    assert (project / "main.py").read_text() == "print('Hello Forge')"


def test_reject_changes(setup_dashboard):
    client, _, request, project = setup_dashboard

    response = client.post(
        f"/approvals/{request.approval_id}/decision",
        json={"decision": "rejected"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "rejected"
    assert not (project / "main.py").exists()


def test_pending_approval_cannot_be_applied(setup_dashboard):
    client, _, request, project = setup_dashboard

    response = client.post(
        f"/approvals/{request.approval_id}/apply"
    )

    assert response.status_code == 409
    assert not (project / "main.py").exists()
