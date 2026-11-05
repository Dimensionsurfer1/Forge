
from unittest.mock import patch

import pytest

from forge.model_router import ModelRouter


def test_select_model():
    router = ModelRouter()

    assert router.select_model("simple_tasks") == "local_qwen"
    assert router.select_model("software_development") == "cloud_coding"


def test_fallback_after_primary_failure():
    router = ModelRouter()

    with patch.object(
        router,
        "_request",
        side_effect=[
            RuntimeError("Cloud unavailable"),
            "Local response",
        ],
    ) as mocked_request:
        result = router.chat(
            messages=[{"role": "user", "content": "Hello"}],
            model="cloud_coding",
        )

    assert result == "Local response"
    assert mocked_request.call_count == 2


def test_failure_after_all_attempts():
    router = ModelRouter()

    with patch.object(
        router,
        "_request",
        side_effect=RuntimeError("Model unavailable"),
    ):
        with pytest.raises(RuntimeError, match="All model attempts failed"):
            router.chat(
                messages=[{"role": "user", "content": "Hello"}],
                model="cloud_coding",
            )
