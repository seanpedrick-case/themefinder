import json
import os
from unittest.mock import MagicMock, patch

import pytest

from themefinder.bedrock_llm import (
    BedrockLLM,
    _normalize_tool_input,
    bedrock_llm_from_env,
)
from themefinder.models import ThemeGenerationResponses, ThemeMappingResponses


@pytest.fixture
def bedrock_llm():
    with patch("themefinder.bedrock_llm.boto3.Session") as session_cls:
        client = MagicMock()
        session_cls.return_value.client.return_value = client
        llm = BedrockLLM(
            "us.anthropic.claude-sonnet-4-5-20250929-v1:0",
            region_name="eu-west-2",
        )
        llm._client = client
        yield llm, client


def test_normalize_tool_input_unwraps_json_string_responses():
    inner = {
        "responses": [
            {
                "topic_label": "frequency",
                "topic_description": "More buses",
                "position": "AGREEMENT",
            }
        ]
    }
    wrapped = {"responses": json.dumps(inner)}
    assert _normalize_tool_input(wrapped) == inner


@pytest.mark.asyncio
async def test_ainvoke_structured_parses_stringified_responses(bedrock_llm):
    llm, client = bedrock_llm
    inner = {
        "responses": [{"response_id": 1, "labels": ["A"]}],
    }
    client.converse.return_value = {
        "output": {
            "message": {
                "content": [
                    {
                        "toolUse": {
                            "name": "themefinder_structured_output",
                            "input": {"responses": json.dumps(inner)},
                        }
                    }
                ]
            }
        }
    }
    result = await llm.ainvoke("prompt", output_model=ThemeMappingResponses)
    assert len(result.parsed.responses) == 1


def test_bedrock_llm_from_env_missing(monkeypatch):
    monkeypatch.delenv("BEDROCK_MODEL_ID", raising=False)
    monkeypatch.delenv("AWS_REGION", raising=False)
    monkeypatch.delenv("AWS_DEFAULT_REGION", raising=False)
    with pytest.raises(ValueError, match="Missing environment variables"):
        bedrock_llm_from_env()


def test_bedrock_llm_from_env_ok(monkeypatch):
    monkeypatch.setenv("BEDROCK_MODEL_ID", "anthropic.claude-3")
    monkeypatch.setenv("AWS_REGION", "eu-west-2")
    monkeypatch.setenv("AWS_PROFILE", "sso-profile")
    with patch("themefinder.bedrock_llm.boto3.Session"):
        llm = bedrock_llm_from_env()
    assert isinstance(llm, BedrockLLM)
    assert llm.model_id == "anthropic.claude-3"


@pytest.mark.asyncio
async def test_ainvoke_structured_uses_tool_config(bedrock_llm):
    llm, client = bedrock_llm
    client.converse.return_value = {
        "output": {
            "message": {
                "content": [
                    {
                        "toolUse": {
                            "name": "themefinder_structured_output",
                            "input": {
                                "responses": [
                                    {"response_id": 1, "labels": ["A"]},
                                ]
                            },
                        }
                    }
                ]
            }
        }
    }
    result = await llm.ainvoke("prompt", output_model=ThemeMappingResponses)
    assert isinstance(result.parsed, ThemeMappingResponses)
    call_kwargs = client.converse.call_args.kwargs
    assert "toolConfig" in call_kwargs
    assert call_kwargs["toolConfig"]["toolChoice"]["tool"]["name"] == (
        "themefinder_structured_output"
    )
    assert "temperature" not in call_kwargs["inferenceConfig"]


@pytest.mark.asyncio
async def test_ainvoke_includes_temperature_when_set(bedrock_llm):
    llm, client = bedrock_llm
    llm.temperature = 0.0
    client.converse.return_value = {
        "output": {"message": {"content": [{"text": "ok"}]}}
    }
    await llm.ainvoke("prompt")
    assert client.converse.call_args.kwargs["inferenceConfig"]["temperature"] == 0.0


@pytest.mark.asyncio
async def test_ainvoke_unstructured(bedrock_llm):
    llm, client = bedrock_llm
    client.converse.return_value = {
        "output": {"message": {"content": [{"text": "hello"}]}}
    }
    result = await llm.ainvoke("prompt")
    assert result.parsed == "hello"
    assert "toolConfig" not in client.converse.call_args.kwargs


@pytest.mark.integration
@pytest.mark.asyncio
async def test_find_themes_smoke_native_bedrock():
    if os.getenv("RUN_BEDROCK_SMOKE") != "1":
        pytest.skip("Set RUN_BEDROCK_SMOKE=1 with AWS credentials and BEDROCK_MODEL_ID")

    import pandas as pd

    from themefinder import find_themes

    df = pd.DataFrame(
        {
            "response_id": [1, 2],
            "response": ["More buses please.", "Better evening service."],
        }
    )
    llm = bedrock_llm_from_env()
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
