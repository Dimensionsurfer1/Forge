import os
from typing import Any

from litellm import completion


class ModelRouter:
    """Provider-independent interface for AI model calls."""

    def chat(
        self,
        messages: list[dict[str, str]],
        model: str,
        temperature: float = 0.2,
        max_tokens: int = 2000,
    ) -> str:
        if not model:
            raise ValueError("A model must be specified.")

        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        # Configure local Ollama.
        if model.startswith("ollama/") or model.startswith("ollama_chat/"):
            kwargs["api_base"] = os.getenv(
                "OLLAMA_API_BASE",
                "http://localhost:11434",
            )

        # Configure OpenRouter.
        elif model.startswith("openrouter/"):
            api_key = os.getenv("OPENROUTER_API_KEY")
            if not api_key:
                raise EnvironmentError(
                    "OPENROUTER_API_KEY is not configured."
                )
            kwargs["api_key"] = api_key

        response = completion(**kwargs)

        content = response.choices[0].message.content

        if not isinstance(content, str):
            raise RuntimeError("The model returned an empty or unsupported response.")

        return content
