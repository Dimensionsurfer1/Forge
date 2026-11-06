
import pytest

from forge.core.workspace import ProjectWorkspace, WorkspaceError


@pytest.fixture
def workspace(tmp_path):
    projects_root = tmp_path / "projects"
    project_root = projects_root / "politag-mun-engine"

    project_root.mkdir(parents=True)

    return ProjectWorkspace(
        projects_root=projects_root,
        project_id="politag-mun-engine",
        max_file_size=100,
    )


def test_write_and_read_file(workspace):
    workspace.write_file("src/main.py", "print('Hello Forge')")

    result = workspace.read_file("src/main.py")

    assert result == "print('Hello Forge')"


def test_create_nested_directories(workspace):
    workspace.write_file(
        "src/api/routes/main.py",
        "def hello(): return 'Hello'",
    )

    assert workspace.read_file("src/api/routes/main.py").startswith(
        "def hello"
    )


def test_list_files(workspace):
    workspace.write_file("src/main.py", "print('Hello')")
    workspace.write_file("README.md", "# Project")

    files = workspace.list_files()

    assert "src/main.py" in files
    assert "README.md" in files


@pytest.mark.parametrize(
    "unsafe_path",
    [
        "../outside.txt",
        "src/../../outside.txt",
        "..\\outside.txt",
        "C:\\Windows\\system.ini",
        "/etc/passwd",
        "src//main.py",
    ],
)
def test_unsafe_paths_are_rejected(workspace, unsafe_path):
    with pytest.raises(WorkspaceError):
        workspace.write_file(unsafe_path, "unsafe")


@pytest.mark.parametrize(
    "protected_path",
    [
        ".env",
        ".env.production",
        ".git/config",
        ".venv/settings.json",
        "node_modules/package/index.js",
        "private.key",
        "certificates/server.pem",
    ],
)
def test_protected_paths_are_rejected(workspace, protected_path):
    with pytest.raises(WorkspaceError):
        workspace.write_file(protected_path, "secret")


def test_protected_files_are_not_listed(workspace):
    workspace.write_file("src/main.py", "print('Hello')")

    # Create protected files directly to simulate an existing project.
    (workspace.root / ".env").write_text("SECRET=value")
    (workspace.root / ".git").mkdir()
    (workspace.root / ".git" / "config").write_text("git config")

    files = workspace.list_files()

    assert "src/main.py" in files
    assert ".env" not in files
    assert ".git/config" not in files


def test_project_id_traversal_is_rejected(tmp_path):
    projects_root = tmp_path / "projects"
    projects_root.mkdir()

    with pytest.raises(WorkspaceError):
        ProjectWorkspace(projects_root, "../outside")


def test_file_size_limit_is_enforced(workspace):
    with pytest.raises(WorkspaceError, match="maximum file size"):
        workspace.write_file("large.txt", "x" * 101)


def test_missing_file_is_rejected(workspace):
    with pytest.raises(WorkspaceError, match="does not exist"):
        workspace.read_file("missing.py")


def test_symlink_escape_is_rejected(workspace, tmp_path):
    outside_file = tmp_path / "outside.txt"
    outside_file.write_text("outside workspace")

    link = workspace.root / "outside-link.txt"

    try:
        link.symlink_to(outside_file)
    except (OSError, NotImplementedError):
        pytest.skip("Symlink creation is not permitted on this system.")

    with pytest.raises(WorkspaceError, match="Symlink"):
        workspace.read_file("outside-link.txt")
