# ThemeFinder

ThemeFinder is a topic modelling Python package designed for analysing one-to-many question-answer data (i.e. survey responses, public consultations, etc.). See the [docs](https://i-dot-ai.github.io/themefinder/) for more info.

> [!IMPORTANT]
> Incubation project: This project is an incubation project; as such, we don't recommend using this for critical use cases yet. We are currently in a research stage, trialling the tool for case studies across the Civil Service. Find out more about our projects at https://ai.gov.uk/. 


## Quickstart

### Install using your package manager of choice

For example `pip install themefinder` or `uv add themefinder`.

### Usage

ThemeFinder takes as input a [pandas DataFrame](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.html) with two columns:
- `response_id`: A unique identifier for each response
- `response`: The free text survey response

ThemeFinder now supports a range of language models through structured outputs.

The function `find_themes` identifies common themes in responses and labels them, it also outputs results from intermediate steps in the theme finding pipeline.

Install `asyncio` (stdlib), `pandas`, and optionally `python-dotenv` for API settings. Pass any object implementing the `LLM` protocol. Use [`BedrockLLM`](docs/bedrock.md) for **AWS Bedrock** (SSO / IAM role), [`OpenAILLM`](src/themefinder/llm.py) for OpenAI, Azure, or OpenAI-compatible gateways.

```python
import asyncio
from dotenv import load_dotenv
import pandas as pd
from themefinder import find_themes, OpenAILLM

load_dotenv()

llm = OpenAILLM(
    model="gpt-4o-2024-08-06",
    request_kwargs={"temperature": 0},
    # api_key=os.environ["OPENAI_API_KEY"],
)

responses_df = pd.DataFrame({
   "response_id": ["1", "2", "3", "4", "5"],
   "response": ["I think it's awesome, I can use it for consultation analysis.",
   "It's great.", "It's a good approach to topic modelling.", "I'm not sure, I need to trial it more.", "I don't like it so much."]
})

question = "What do you think of ThemeFinder?"
system_prompt = "You are an AI evaluation tool analyzing survey responses about a Python package."

async def main():
    result = await find_themes(responses_df, llm, question, system_prompt=system_prompt)
    print(result)

if __name__ == "__main__":
    asyncio.run(main())
```

### AWS Bedrock (native — recommended)

Use boto3’s **credential chain** (IAM Identity Center / `AWS_PROFILE`, session env vars, or instance role). No LiteLLM proxy required. See [docs/bedrock.md](docs/bedrock.md).

```bash
aws sso login --profile your-org-profile
export AWS_PROFILE=your-org-profile
export AWS_REGION=eu-west-2
export BEDROCK_MODEL_ID=us.anthropic.claude-sonnet-4-5-20250929-v1:0
```

```python
from themefinder import find_themes, bedrock_llm_from_env

llm = bedrock_llm_from_env()
result = await find_themes(responses_df, llm, question=question, system_prompt=system_prompt)
```

Smoke test: `uv run python examples/bedrock_bedrock.py`.

### AWS Bedrock (optional LiteLLM gateway)

If you need a shared OpenAI-compatible proxy, use a **pinned** [LiteLLM deploy](deploy/litellm/README.md) and `openai_llm_from_gateway_env()` — see [HARDENING.md](deploy/litellm/HARDENING.md). Prefer native `BedrockLLM` when possible.

For Azure OpenAI via a central gateway (as used in evals), set `LLM_GATEWAY_URL`, `CONSULT_EVAL_LITELLM_API_KEY`, and your deployment name on `OpenAILLM(model=...)`.

## ThemeFinder pipeline

ThemeFinder's pipeline consists of five distinct stages, each utilizing a specialized LLM prompt:

### Sentiment analysis
- Analyses the emotional tone and position of each response using sentiment-focused prompts
- Provides structured sentiment categorisation based on LLM analysis

### Theme generation
- Uses exploratory prompts to identify initial themes from response batches
- Groups related responses for better context through guided theme extraction

### Theme condensation
- Employs comparative prompts to combine similar or overlapping themes
- Reduces redundancy in identified topics through systematic theme evaluation

### Theme refinement
- Leverages standardisation prompts to normalise theme descriptions
- Creates clear, consistent theme definitions through structured refinement

### Theme target alignment
- Optional step to consolidate themes down to a target number

### Theme mapping
- Utilizes classification prompts to map individual responses to refined themes
- Supports multiple theme assignments per response through detailed analysis


The prompts used at each stage can be found in `src/themefinder/prompts/`.

The file [`src/themefinder/tasks.py`](src/themefinder/tasks.py) contains `find_themes` and the individual pipeline stages.


**For more detail - see the docs: [https://i-dot-ai.github.io/themefinder/](https://i-dot-ai.github.io/themefinder/).**


## Model Compatibility

ThemeFinder's structured output approach makes it compatible with a wide range of language models from various providers. This list is non-exhaustive, and other models may also work effectively:

### OpenAI Models
- GPT-4, GPT-4o, GPT-4.1
- All Azure OpenAI deployments

### Google Models
- Gemini series (1.5 Pro, 2.0 Pro, etc.)

### Anthropic Models
- Claude series (Claude 3 Opus, Sonnet, Haiku, etc.)
- Claude on **AWS Bedrock** (native `BedrockLLM` or optional LiteLLM gateway)

### AWS Bedrock
- Anthropic Claude and other Bedrock foundation models via [`BedrockLLM`](docs/bedrock.md)

### Open Source Models
- Llama 2, Llama 3
- Mistral models (e.g., Mistral 7B, Mixtral)


## Setting up a consultation

To set up a new consultation, run:

```bash
make setup-consultation NAME=my_consultation
```

Or without a name (you'll be prompted):

```bash
make setup-consultation
```

This will:
1. Create a folder under `./consultations/<name>/`
2. Prompt you to copy in the consultation response data and template question understanding file
3. Ask you to identify which file is which
4. Process the data and generate the required input files under `./consultations/<name>/inputs/`
5. Upload the files to S3 to `i-dot-ai-prod-consult-data/app_data/consultations/<name>/inputs/`

#### Optional flags

| Makefile variable | Description |
|---|---|
| `UNTIL=validate` | Stop after validation — no files are written and no upload is performed. Useful for a quick sanity-check. |
| `UNTIL=build` | Validate and write local files, but skip uploading to S3. |
| `DIR=<path>` | Path to an existing consultation directory (skips the interactive prompt to create one). |
| `RESPONSES=<path>` | Path to the response data file (skips file-selection prompt). |
| `QU=<path>` | Path to the question understanding Excel file (skips file-selection prompt). |

By default, the pipeline runs all three stages: **validate → build → upload**.

Examples:

```bash
# Full pipeline (validate + build + upload to S3)
make setup-consultation NAME=my_consultation

# Validate only
make setup-consultation NAME=my_consultation UNTIL=validate

# Build files locally without uploading with file paths specified
make setup-consultation NAME=my_consultation \
    RESPONSES=path/to/responses.xlsx \
    QU=path/to/question_understanding.xlsx \
    UNTIL=build

```

For further instructions on setting up the consultation in the app, see the [Confluence guide](https://incubatorforartificialintelligence.atlassian.net/wiki/spaces/Consult/pages/136445956/1.2+Set+up+the+consultation+in+the+app).


## Development

This project uses [uv](https://docs.astral.sh/uv/) for dependency management.

```bash
# Clone and set up development environment
git clone https://github.com/i-dot-ai/themefinder.git
cd themefinder
uv sync --extra dev
source .venv/bin/activate

# Run tests
pytest tests/

# Run linting
pre-commit run --all-files
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

The documentation is [© Crown copyright](https://www.nationalarchives.gov.uk/information-management/re-using-public-sector-information/uk-government-licensing-framework/crown-copyright/) and available under the terms of the [Open Government 3.0 licence](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/).


## Feedback

Contact us with questions or feedback at packages@cabinetoffice.gov.uk.
