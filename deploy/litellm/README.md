# Bedrock gateway for ThemeFinder (LiteLLM, optional)

**Prefer native Bedrock:** [`BedrockLLM`](../../src/themefinder/bedrock_llm.py) with SSO / IAM (see [docs/bedrock.md](../../docs/bedrock.md)) avoids running a separate proxy.

This folder documents a **pinned** LiteLLM proxy that exposes `/v1/chat/completions` to AWS Bedrock for teams that need a shared gateway. ThemeFinder uses [`OpenAILLM`](../../src/themefinder/llm.py) with `base_url` pointing at the proxy.

## Quick start (local)

```bash
cd deploy/litellm
python -m venv .venv
.venv/Scripts/activate   # or source .venv/bin/activate
pip install -r requirements.txt
python verify_litellm_install.py

export AWS_REGION=eu-west-2
export LITELLM_MASTER_KEY=your-secret-master-key

litellm --config config.yaml --port 4000
```

OpenAI-compatible base URL: `http://127.0.0.1:4000/v1`

## Docker

```bash
cd deploy/litellm
# Optional: set LITELLM_IMAGE to a digest-pinned image in .env
docker compose up -d
docker compose exec litellm python /app/deploy/litellm/verify_litellm_install.py  # if bundled; else run verify on host venv
```

Mount and verify using the host venv script before routing production traffic.

## ThemeFinder

Set in `.env` (see [`.env.example`](../../.env.example)):

- `LLM_GATEWAY_URL=http://127.0.0.1:4000/v1`
- `LITELLM_API_KEY=<LITELLM_MASTER_KEY or virtual key>`
- `BEDROCK_LITELLM_MODEL=themefinder-claude`

Run the smoke example:

```bash
uv run python examples/bedrock_litellm.py
```

## Security

See [HARDENING.md](HARDENING.md) and [LiteLLM’s incident post](https://docs.litellm.ai/blog/security-incident-oct-21-2026).
