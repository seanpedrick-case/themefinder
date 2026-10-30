"""Smoke test: ThemeFinder pipeline via LiteLLM gateway → AWS Bedrock.

Requires a running LiteLLM proxy (see deploy/litellm/README.md) and .env:

    LLM_GATEWAY_URL=http://127.0.0.1:4000/v1
    LITELLM_API_KEY=<master or virtual key>
    BEDROCK_LITELLM_MODEL=themefinder-claude

Run:
    uv run python examples/bedrock_litellm.py
"""

from __future__ import annotations

import asyncio
import os
import sys

import pandas as pd
from dotenv import load_dotenv

from themefinder import find_themes, openai_llm_from_gateway_env

load_dotenv()

QUESTION = "What improvements would you most like to see in local public transportation?"
SYSTEM_PROMPT = (
    "You are analysing free-text survey responses about public transportation."
)

SAMPLE = pd.DataFrame(
    {
        "response_id": [1, 2, 3, 4, 5],
        "response": [
            "Buses need to run more frequently during rush hour.",
            "Real-time tracking would help if it is accurate.",
            "Evening and weekend service is poor.",
            "The morning bus is late too often.",
            "More night buses on main routes would help shift workers.",
        ],
    }
)


async def run_smoke(*, concurrency: int = 2) -> dict:
    llm = openai_llm_from_gateway_env()
    return await find_themes(
        SAMPLE,
        llm,
        question=QUESTION,
        system_prompt=SYSTEM_PROMPT,
        verbose=True,
        concurrency=concurrency,
    )


def main() -> int:
    if os.getenv("SKIP_BEDROCK_SMOKE") == "1":
        print("SKIP_BEDROCK_SMOKE=1 set; exiting without calling the gateway.")
        return 0
    try:
        result = asyncio.run(run_smoke())
    except ValueError as exc:
        print(exc, file=sys.stderr)
        print(
            "Start the proxy (deploy/litellm) and set LLM_GATEWAY_URL, "
            "LITELLM_API_KEY, BEDROCK_LITELLM_MODEL.",
            file=sys.stderr,
        )
        return 1
    except Exception as exc:
        print(f"Smoke test failed: {exc}", file=sys.stderr)
        return 2

    themes = result.get("themes")
    if themes is None or len(themes) == 0:
        print("Pipeline returned no themes.", file=sys.stderr)
        return 3

    print("Smoke test OK.")
    print(themes.head())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
