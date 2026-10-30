"""LLM abstraction layer for themefinder.

Provides a Protocol-based interface for LLM calls with structured output support,
and an OpenAI implementation. Designed for easy extension to other providers.
"""

import asyncio
import concurrent.futures
import os
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

import openai
from pydantic import BaseModel


@dataclass
class LLMResponse:
    """Wraps an LLM call result."""

    parsed: BaseModel | str


@runtime_checkable
class LLM(Protocol):
    """Protocol defining the LLM interface for themefinder."""

    async def ainvoke(
        self, prompt: str, output_model: type[BaseModel] | None = None
    ) -> LLMResponse: ...

    def invoke(
        self, prompt: str, output_model: type[BaseModel] | None = None
    ) -> LLMResponse: ...


class OpenAILLM:
    """OpenAI SDK implementation of the LLM protocol."""

    def __init__(
        self,
        model,
        request_kwargs: dict | None = None,
        **client_kwargs,
    ):
        self.model = model
        self.request_kwargs = request_kwargs or {}
        self.client = openai.AsyncOpenAI(**client_kwargs)

    async def ainvoke(
        self, prompt: str, output_model: type[BaseModel] | None = None
    ) -> LLMResponse:
        kwargs = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            **self.request_kwargs,
        }
        if output_model:
            kwargs["response_format"] = output_model
            response = await self.client.chat.completions.parse(**kwargs)
            return LLMResponse(parsed=response.choices[0].message.parsed)
        else:
            response = await self.client.chat.completions.create(**kwargs)
            return LLMResponse(parsed=response.choices[0].message.content)

    def invoke(
        self, prompt: str, output_model: type[BaseModel] | None = None
    ) -> LLMResponse:
        """Synchronous wrapper around ainvoke."""
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


def openai_llm_from_gateway_env(
    *,
    model_env: str = "BEDROCK_LITELLM_MODEL",
    gateway_url_env: str = "LLM_GATEWAY_URL",
    api_key_env: str = "LITELLM_API_KEY",
    fallback_api_key_env: str = "CONSULT_EVAL_LITELLM_API_KEY",
    temperature: float = 0.0,
    timeout: int = 600,
) -> OpenAILLM:
    """Build an ``OpenAILLM`` client for a LiteLLM (or other OpenAI-compatible) gateway.

    Used for AWS Bedrock when the proxy is configured with a Bedrock ``model_list`` entry
    (see ``deploy/litellm/config.yaml``).
    """
    model = os.getenv(model_env)
    base_url = os.getenv(gateway_url_env)
    api_key = os.getenv(api_key_env) or os.getenv(fallback_api_key_env)
    missing: list[str] = []
    if not model:
        missing.append(model_env)
    if not base_url:
        missing.append(gateway_url_env)
    if not api_key:
        missing.append(f"{api_key_env} or {fallback_api_key_env}")
    if missing:
        raise ValueError(
            "Missing environment variables for gateway LLM: "
            + ", ".join(missing)
        )
    return OpenAILLM(
        model=model,
        request_kwargs={"temperature": temperature},
        base_url=base_url,
        api_key=api_key,
        timeout=timeout,
    )
