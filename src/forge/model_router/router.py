import os
from pathlib import Path
from typing import Any

import litellm
from dotenv import load_dotenv

from forge.model_router.config_loader import (
    ModelSettings,
    load_model_settings,
)


class ModelRouter:
    def __init__(
        self,
        settings: ModelSettings | None = None,
    ):
        project_root = Path(__file__).resolve().parents[3]
        load_dotenv(project_root / ".env")

        self.settings = settings or load_model_settings()

    def resolve_model(self, model_id: str) -> tuple[str, dict[str, Any]]:
        model_config = self.settings.get_model(model_id)

        provider = self.settings.providers[model_config.provider]

        if not provider.enabled:
            raise ValueError(
                f"Provider '{model_config.provider}' is disabled."
            )

        if model_config.litellm_model:
            litellm_model = model_config.litellm_model

        elif model_config.litellm_model_env:
            litellm_model = os.getenv(model_config.litellm_model_env)

            if not litellm_model:
                raise ValueError(
                    f"Missing environment variable: "
                    f"{model_config.litellm_model_env}"
                )
        else:
            raise ValueError(
                f"No LiteLLM model configured for '{model_id}'."
            )

        kwargs: dict[str, Any] = {}

        if provider.api_key_env:
            api_key = os.getenv(provider.api_key_env)

            if not api_key:
                raise ValueError(
                    f"Missing API key environment variable: "
                    f"{provider.api_key_env}"
                )

            kwargs["api_key"] = api_key

        if provider.api_base:
            kwargs["api_base"] = provider.api_base

        return litellm_model, kwargs

    def chat(
        self,
        messages: list[dict[str, str]],
        model: str,
        temperature: float = 0.2,
        max_tokens: int = 2000,
    ) -> str:
        litellm_model, provider_kwargs = self.resolve_model(model)

        response = litellm.completion(
            model=litellm_model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **provider_kwargs,
        )

        content = response.choices[0].message.content

        if not isinstance(content, str):
            raise ValueError("Model returned an empty or non-text response.")

        return content