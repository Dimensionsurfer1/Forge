
import os
import re
import tempfile
from pathlib import Path
from typing import Union


PathInput = Union[str, Path]

PROTECTED_DIRECTORIES = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".secrets",
}

PROTECTED_SUFFIXES = {
    ".pem",
    ".key",
    ".p12",
    ".pfx",
}


class WorkspaceError(ValueError):
    """Raised when a workspace operation violates its boundaries."""


class ProjectWorkspace:
    def __init__(
        self,
        projects_root: PathInput,
        project_id: str,
        max_file_size: int = 1_000_000,
    ):
        if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_-]*", project_id):
            raise WorkspaceError("Invalid project ID.")

        if max_file_size < 1:
            raise ValueError("max_file_size must be positive.")

        self.projects_root = Path(projects_root).resolve(strict=True)

        if not self.projects_root.is_dir():
            raise WorkspaceError("Projects root must be a directory.")

        self.root = self.projects_root / project_id

        if self.root.is_symlink():
            raise WorkspaceError("Project directory cannot be a symlink.")

        if not self.root.exists() or not self.root.is_dir():
            raise WorkspaceError("Project directory does not exist.")

        self.root = self.root.resolve(strict=True)

        if not self._is_inside(self.root, self.projects_root):
            raise WorkspaceError("Project directory is outside projects root.")

        self.max_file_size = max_file_size

    @staticmethod
    def _is_inside(path: Path, parent: Path) -> bool:
        try:
            path.relative_to(parent)
            return True
        except ValueError:
            return False

    @staticmethod
    def _is_protected(parts: tuple[str, ...]) -> bool:
        for part in parts:
            name = part.lower()

            if name in PROTECTED_DIRECTORIES:
                return True

            if name == ".env" or name.startswith(".env."):
                return True

            if Path(name).suffix in PROTECTED_SUFFIXES:
                return True

        return False

    def _resolve(self, relative_path: PathInput) -> Path:
        raw_path = str(relative_path)

        if not raw_path or "\x00" in raw_path:
            raise WorkspaceError("Invalid file path.")

        normalized = raw_path.replace("\\", "/")

        if (
            normalized.startswith("/")
            or re.match(r"^[a-zA-Z]:", normalized)
        ):
            raise WorkspaceError("Absolute paths are not allowed.")

        parts = tuple(normalized.split("/"))

        if any(part in ("", ".", "..") for part in parts):
            raise WorkspaceError("Invalid or unsafe relative path.")

        if any(":" in part for part in parts):
            raise WorkspaceError("Colon characters are not allowed.")

        if any(part.endswith((".", " ")) for part in parts):
            raise WorkspaceError("Invalid Windows file name.")

        if self._is_protected(parts):
            raise WorkspaceError("Access to this path is protected.")

        candidate = self.root.joinpath(*parts)
        current = self.root

        # Reject symlinks and Windows junctions in every path component.
        for part in parts:
            current = current / part

            is_junction = getattr(current, "is_junction", lambda: False)()

            if current.is_symlink() or is_junction:
                raise WorkspaceError("Symlink paths are not allowed.")

        resolved = candidate.resolve(strict=False)

        if not self._is_inside(resolved, self.root):
            raise WorkspaceError("Path escapes the project workspace.")

        return candidate

    def read_file(self, relative_path: PathInput) -> str:
        """Read a UTF-8 text file from the project workspace."""

        path = self._resolve(relative_path)

        if not path.exists() or not path.is_file():
            raise WorkspaceError("File does not exist.")

        if path.stat().st_size > self.max_file_size:
            raise WorkspaceError("File exceeds the maximum allowed size.")

        return path.read_text(encoding="utf-8")

    def write_file(
        self,
        relative_path: PathInput,
        content: str,
    ) -> None:
        """Create or replace a UTF-8 text file safely."""

        if not isinstance(content, str):
            raise TypeError("File content must be a string.")

        encoded = content.encode("utf-8")

        if len(encoded) > self.max_file_size:
            raise WorkspaceError("Content exceeds the maximum file size.")

        path = self._resolve(relative_path)

        if path.exists() and not path.is_file():
            raise WorkspaceError("Target path is not a regular file.")

        # Create missing parent directories one at a time.
        current = self.root

        for part in path.relative_to(self.root).parts[:-1]:
            current = current / part
            current.mkdir(exist_ok=True)

            if current.is_symlink():
                raise WorkspaceError("Symlink directories are not allowed.")

            if getattr(current, "is_junction", lambda: False)():
                raise WorkspaceError("Junction directories are not allowed.")

        # Recheck the path after creating parent directories.
        path = self._resolve(relative_path)

        if path.exists() and not path.is_file():
            raise WorkspaceError("Target path is not a regular file.")

        # Use a temporary file and atomic replacement.
        temporary_path = None

        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=path.parent,
                prefix=".forge-tmp-",
                delete=False,
            ) as temporary_file:
                temporary_path = Path(temporary_file.name)
                temporary_file.write(content)
                temporary_file.flush()
                os.fsync(temporary_file.fileno())

            # Revalidate before replacing the destination.
            path = self._resolve(relative_path)

            if path.exists() and not path.is_file():
                raise WorkspaceError("Target path is not a regular file.")

            os.replace(temporary_path, path)
            temporary_path = None

        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)

    def list_files(self, max_files: int = 500) -> list[str]:
        """List accessible project files using relative paths."""

        if max_files < 1:
            raise ValueError("max_files must be positive.")

        results = []

        for current_root, directories, filenames in os.walk(
            self.root,
            topdown=True,
            followlinks=False,
        ):
            current_path = Path(current_root)

            directories[:] = [
                name
                for name in directories
                if not (current_path / name).is_symlink()
                and not getattr(
                    current_path / name, "is_junction", lambda: False
                )()
                and not self._is_protected(
                    (name,)
                )
            ]

            for filename in filenames:
                file_path = current_path / filename

                if file_path.is_symlink():
                    continue

                if getattr(file_path, "is_junction", lambda: False)():
                    continue

                relative = file_path.relative_to(self.root)
                parts = tuple(relative.parts)

                if self._is_protected(parts):
                    continue

                results.append(relative.as_posix())

                if len(results) >= max_files:
                    return sorted(results)

        return sorted(results)

    def validate_file_path(self, relative_path: PathInput) -> Path:
        """Validate a proposed file path without modifying it."""
        path = self._resolve(relative_path)

        if path.exists() and not path.is_file():
            raise WorkspaceError("Target path is not a regular file.")

        return path
