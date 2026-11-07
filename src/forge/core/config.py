
import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[3]


def load_forge_config() -> dict[str, Any]:
    """Load environment variables and Forge YAML configuration."""

    load_dotenv(PROJECT_ROOT / ".env")

    config_path = PROJECT_ROOT / "config" / "forge.yaml"

    with config_path.open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file) or {}

    projects_root = os.getenv("FORGE_PROJECTS_ROOT")

    if not projects_root:
        raise ValueError(
            "FORGE_PROJECTS_ROOT is missing from the environment."
        )

    config.setdefault("storage", {})
    config["storage"]["projects"] = str(
        Path(projects_root).expanduser().resolve()
    )

    database_path = Path(config["storage"]["database"])

    if not database_path.is_absolute():
        config["storage"]["database"] = str(
            PROJECT_ROOT / database_path
        )

    return config
