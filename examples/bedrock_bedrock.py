"""Smoke test: ThemeFinder via native AWS Bedrock (boto3 / SSO credential chain).

Prerequisites:
    aws sso login --profile YOUR_PROFILE   # or other valid AWS credentials

Environment:
    AWS_PROFILE=YOUR_PROFILE               # optional if using env keys or IAM role
    AWS_REGION=eu-west-2
    BEDROCK_MODEL_ID=us.anthropic.claude-sonnet-4-5-20250929-v1:0

Run:
    uv run python examples/bedrock_bedrock.py

Optional:
    BEDROCK_OUTPUT_DIR=examples/output/bedrock   # CSV export directory (default)
    BEDROCK_SKIP_EXPORT=1                        # skip writing CSV files
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

from themefinder import bedrock_llm_from_env, find_themes

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

DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent / "output" / "bedrock"


def export_results(result: dict, output_dir: Path) -> list[Path]:
    """Write pipeline DataFrames to CSV under ``output_dir``."""
    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    exports = [
        ("themes", result.get("themes")),
        ("mapping", result.get("mapping")),
        ("detailed_responses", result.get("detailed_responses")),
        ("unprocessables", result.get("unprocessables")),
    ]
    for name, frame in exports:
        if frame is None or not isinstance(frame, pd.DataFrame) or frame.empty:
            continue
        path = output_dir / f"{name}.csv"
        frame.to_csv(path, index=False)
        written.append(path)
    return written


async def run_smoke(*, concurrency: int = 2) -> dict:
    llm = bedrock_llm_from_env()
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
        print("SKIP_BEDROCK_SMOKE=1 set; exiting without calling Bedrock.")
        return 0
    try:
        result = asyncio.run(run_smoke())
    except ValueError as exc:
        print(exc, file=sys.stderr)
        print(
            "Set BEDROCK_MODEL_ID and AWS_REGION, then authenticate "
            "(e.g. aws sso login --profile YOUR_PROFILE and AWS_PROFILE).",
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

    if os.getenv("BEDROCK_SKIP_EXPORT") != "1":
        out_dir = Path(os.getenv("BEDROCK_OUTPUT_DIR", DEFAULT_OUTPUT_DIR))
        paths = export_results(result, out_dir)
        if paths:
            print(f"Wrote {len(paths)} file(s) to {out_dir}:")
            for path in paths:
                print(f"  {path}")
        else:
            print("No non-empty tables to export.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
