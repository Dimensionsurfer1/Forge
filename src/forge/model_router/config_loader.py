from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field


class ProviderConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    type: Literal["cloud", "local"]
    api_key_env: str | None = None
    api_base: str | None = None


class ModelConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: str
    litellm_model: str | None = None
    litellm_model_env: str | None = None
    context_window: int | None = None
    capabilities: list[str] = Field(default_factory=list)
    cost_tier: str


class EscalationConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    max_attempts: int = 2


class LocalExecutionConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    max_parallel_requests: int = 1
    preferred_context_window: int = 4096


class RoutingConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    strategy: Literal["balanced", "quality_first", "cost_first"]
    default_model: str
    local_fallback: str | None = None
    escalation: EscalationConfig = Field(default_factory=EscalationConfig)
    rules: dict[str, str] = Field(default_factory=dict)
    local_execution: LocalExecutionConfig = Field(
        default_factory=LocalExecutionConfig
    )


class ModelSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    providers: dict[str, ProviderConfig]
    models: dict[str, ModelConfig]
    routing: RoutingConfig

    def validate_references(self) -> None:
        for name, model in self.models.items():
            if model.provider not in self.providers:
                raise ValueError(
                    f"Model '{name}' references unknown provider "
                    f"'{model.provider}'."
                )

        references = [
            self.routing.default_model,
            *self.routing.rules.values(),
        ]

        if self.routing.local_fallback:
            references.append(self.routing.local_fallback)

        for name in references:
            if name not in self.models:
                raise ValueError(f"Unknown model reference: '{name}'.")

    def get_model(self, model_id: str) -> ModelConfig:
        try:
            return self.models[model_id]
        except KeyError:
            raise KeyError(f"Model not configured: {model_id}") from None


def load_model_settings(
    config_path: str | Path | None = None,
) -> ModelSettings:
    if config_path is None:
        project_root = Path(__file__).resolve().parents[3]
        config_path = project_root / "config" / "models.yaml"

    path = Path(config_path)

    if not path.exists():
        raise FileNotFoundError(f"Model configuration not found: {path}")

    with path.open("r", encoding="utf-8-sig") as file:
        data: Any = yaml.safe_load(file)

    if not isinstance(data, dict):
        raise ValueError("Invalid model configuration.")

    settings = ModelSettings.model_validate(data)
    settings.validate_references()

    return settings
