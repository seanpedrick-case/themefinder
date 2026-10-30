import os

import pytest

from themefinder.llm import OpenAILLM, openai_llm_from_gateway_env


def test_openai_llm_from_gateway_env_missing_vars(monkeypatch):
    monkeypatch.delenv("BEDROCK_LITELLM_MODEL", raising=False)
    monkeypatch.delenv("LLM_GATEWAY_URL", raising=False)
    monkeypatch.delenv("LITELLM_API_KEY", raising=False)
    monkeypatch.delenv("CONSULT_EVAL_LITELLM_API_KEY", raising=False)
    with pytest.raises(ValueError, match="Missing environment variables"):
        openai_llm_from_gateway_env()


def test_openai_llm_from_gateway_env_builds_client(monkeypatch):
    monkeypatch.setenv("BEDROCK_LITELLM_MODEL", "themefinder-claude")
    monkeypatch.setenv("LLM_GATEWAY_URL", "http://127.0.0.1:4000/v1")
    monkeypatch.setenv("LITELLM_API_KEY", "test-key")

    llm = openai_llm_from_gateway_env()
    assert isinstance(llm, OpenAILLM)
    assert llm.model == "themefinder-claude"


def test_openai_llm_from_gateway_env_fallback_api_key(monkeypatch):
    monkeypatch.setenv("BEDROCK_LITELLM_MODEL", "themefinder-claude")
    monkeypatch.setenv("LLM_GATEWAY_URL", "http://127.0.0.1:4000/v1")
    monkeypatch.delenv("LITELLM_API_KEY", raising=False)
    monkeypatch.setenv("CONSULT_EVAL_LITELLM_API_KEY", "eval-key")

    openai_llm_from_gateway_env()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_find_themes_smoke_via_gateway():
    if os.getenv("RUN_BEDROCK_GATEWAY_SMOKE") != "1":
        pytest.skip("Set RUN_BEDROCK_GATEWAY_SMOKE=1 with a live LiteLLM proxy")

    import pandas as pd

    from themefinder import find_themes

    df = pd.DataFrame(
        {
            "response_id": [1, 2],
            "response": ["More buses please.", "Better evening service."],
        }
    )
    llm = openai_llm_from_gateway_env()
    result = await find_themes(
        df,
        llm,
        question="What transport improvements do you want?",
        system_prompt="You analyse survey responses.",
        verbose=False,
        concurrency=2,
    )
    assert result["themes"] is not None
    assert len(result["themes"]) > 0
