"""AWS Bedrock Runtime LLM via boto3 Converse (SSO / default credential chain)."""

from __future__ import annotations

import asyncio
import concurrent.futures
import json
import os
from typing import Any

import boto3
from botocore.config import Config
from pydantic import BaseModel, ValidationError

from themefinder.bedrock_schema import bedrock_json_schema
from themefinder.llm import LLMResponse

_STRUCTURED_TOOL_NAME = "themefinder_structured_output"


def _parse_json_value(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    text = value.strip()
    if not text or text[0] not in "{[":
        return value
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return value


def _normalize_tool_input(raw_input: Any) -> Any:
    """Coerce Bedrock tool payloads (sometimes JSON-encoded strings) into objects."""
    raw_input = _parse_json_value(raw_input)
    if not isinstance(raw_input, dict):
        return raw_input

    normalized: dict[str, Any] = {
        key: _parse_json_value(val) for key, val in raw_input.items()
    }
    responses = normalized.get("responses")
    if isinstance(responses, str):
        responses = _parse_json_value(responses)
    if isinstance(responses, dict) and "responses" in responses:
        return responses
    if isinstance(responses, list):
        normalized["responses"] = responses
    return normalized


class BedrockLLM:
    """Bedrock Converse client implementing the ThemeFinder ``LLM`` protocol."""

    def __init__(
        self,
        model_id: str,
        *,
        region_name: str,
        profile_name: str | None = None,
        max_tokens: int = 8192,
        temperature: float | None = None,
        read_timeout: int = 600,
    ):
        self.model_id = model_id
        self.max_tokens = max_tokens
        self.temperature = temperature
        session = (
            boto3.Session(profile_name=profile_name)
            if profile_name
            else boto3.Session()
        )
        self._client = session.client(
            "bedrock-runtime",
            region_name=region_name,
            config=Config(read_timeout=read_timeout, retries={"max_attempts": 3}),
        )

    def _inference_config(self) -> dict[str, Any]:
        config: dict[str, Any] = {"maxTokens": self.max_tokens}
        # Claude Sonnet 5+ on Bedrock reject ``temperature`` in Converse (use model defaults).
        if self.temperature is not None:
            config["temperature"] = self.temperature
        return config

    def _converse(
        self,
        prompt: str,
        output_model: type[BaseModel] | None,
    ) -> LLMResponse:
        messages = [
            {"role": "user", "content": [{"text": prompt}]},
        ]
        kwargs: dict[str, Any] = {
            "modelId": self.model_id,
            "messages": messages,
            "inferenceConfig": self._inference_config(),
        }
        if output_model is not None:
            schema_name, schema = bedrock_json_schema(output_model)
            kwargs["toolConfig"] = {
                "tools": [
                    {
                        "toolSpec": {
                            "name": _STRUCTURED_TOOL_NAME,
                            "description": (
                                f"Return JSON matching the {schema_name} schema."
                            ),
                            "inputSchema": {"json": schema},
                        }
                    }
                ],
                "toolChoice": {"tool": {"name": _STRUCTURED_TOOL_NAME}},
            }

        response = self._client.converse(**kwargs)
        return self._parse_converse_response(response, output_model)

    @staticmethod
    def _parse_converse_response(
        response: dict[str, Any],
        output_model: type[BaseModel] | None,
    ) -> LLMResponse:
        content = response.get("output", {}).get("message", {}).get("content", [])
        if output_model is not None:
            for block in content:
                tool_use = block.get("toolUse")
                if tool_use and tool_use.get("name") == _STRUCTURED_TOOL_NAME:
                    raw_input = _normalize_tool_input(tool_use.get("input"))
                    return LLMResponse(
                        parsed=output_model.model_validate(raw_input)
                    )
            for block in content:
                text = block.get("text")
                if text:
                    raw_input = _normalize_tool_input(_parse_json_value(text))
                    return LLMResponse(
                        parsed=output_model.model_validate(raw_input)
                    )
            raise ValueError("Bedrock response did not include structured tool output")

        texts = [block["text"] for block in content if "text" in block]
        if not texts:
            raise ValueError("Bedrock response did not include text content")
        return LLMResponse(parsed="\n".join(texts))

    async def ainvoke(
        self, prompt: str, output_model: type[BaseModel] | None = None
    ) -> LLMResponse:
        return await asyncio.to_thread(self._converse, prompt, output_model)

    def invoke(
        self, prompt: str, output_model: type[BaseModel] | None = None
    ) -> LLMResponse:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        if loop and loop.is_running():
            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(
                    asyncio.run, self.ainvoke(prompt, output_model)
                ).result()
        return asyncio.run(self.ainvoke(prompt, output_model))


def bedrock_llm_from_env(
    *,
    model_id_env: str = "BEDROCK_MODEL_ID",
    region_env: str = "AWS_REGION",
    fallback_region_env: str = "AWS_DEFAULT_REGION",
    profile_env: str = "AWS_PROFILE",
    max_tokens: int = 8192,
    temperature_env: str = "BEDROCK_TEMPERATURE",
) -> BedrockLLM:
    """Build ``BedrockLLM`` using the boto3 credential chain (SSO profile, env keys, or IAM role)."""
    model_id = os.getenv(model_id_env)
    region = os.getenv(region_env) or os.getenv(fallback_region_env)
    profile = os.getenv(profile_env) or None
    temp_raw = os.getenv(temperature_env)
    temperature = float(temp_raw) if temp_raw not in (None, "") else None
    missing: list[str] = []
    if not model_id:
        missing.append(model_id_env)
    if not region:
        missing.append(f"{region_env} or {fallback_region_env}")
    if missing:
        raise ValueError(
            "Missing environment variables for Bedrock LLM: " + ", ".join(missing)
        )
    return BedrockLLM(
        model_id=model_id,
        region_name=region,
        profile_name=profile,
        max_tokens=max_tokens,
        temperature=temperature,
    )
