# AWS Bedrock (native)

ThemeFinder can call **Amazon Bedrock** directly with [`BedrockLLM`](../src/themefinder/bedrock_llm.py) and the standard **boto3 credential chain**—no LiteLLM proxy required.

## Authentication

| Method | Setup |
|--------|--------|
| **IAM Identity Center (SSO)** | `aws sso login --profile YOUR_PROFILE`, then `AWS_PROFILE=YOUR_PROFILE` |
| **Short-lived keys** | `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN` |
| **IAM role** | Run on EC2, ECS, Lambda, etc. with a role that can invoke Bedrock |
| **Bedrock API key** | If enabled in your account, set `AWS_BEARER_TOKEN_BEDROCK` (see AWS docs) |

Prefer SSO or IAM roles over long-lived access keys in `.env` files.

## Environment

- `BEDROCK_MODEL_ID` — foundation model ID enabled in your region
- `AWS_REGION` or `AWS_DEFAULT_REGION`
- `AWS_PROFILE` — optional SSO profile name
- `BEDROCK_TEMPERATURE` — optional; omit for Claude Sonnet 5+ (Bedrock rejects `temperature` on those models)

## Example

```bash
aws sso login --profile your-org-profile
export AWS_PROFILE=your-org-profile
export AWS_REGION=eu-west-2
export BEDROCK_MODEL_ID=us.anthropic.claude-sonnet-4-5-20250929-v1:0
uv run python examples/bedrock_bedrock.py
```

Structured pipeline stages use Bedrock **tool calling** with JSON schemas derived from Pydantic models ([`bedrock_schema.py`](../src/themefinder/bedrock_schema.py)).

## Data and security

Consultation free text is sent to Bedrock in **your** AWS account. Align usage with your organisation’s data-handling requirements.

## LiteLLM gateway (optional)

An OpenAI-compatible proxy is still documented under [`deploy/litellm/`](../deploy/litellm/README.md) if you need a shared gateway; native `BedrockLLM` avoids an extra hop and LiteLLM supply-chain exposure.
