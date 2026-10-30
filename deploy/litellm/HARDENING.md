# LiteLLM proxy hardening (ThemeFinder + Bedrock)

ThemeFinder talks to Bedrock through an **OpenAI-compatible LiteLLM proxy**. The proxy holds AWS credentials and sees consultation free text—treat it as production infrastructure.

## Supply chain

- Pin versions in [`requirements.txt`](requirements.txt) (`litellm==1.106.6` or a version you have verified after [the Oct 2026 incident](https://docs.litellm.ai/blog/security-incident-oct-21-2026)).
- **Never** use Docker tags `:latest`, `:main-latest`, or `:main-stable`. Pin `ghcr.io/berriai/litellm:v1.106.6` **by digest** in production.
- Run [`verify_litellm_install.py`](verify_litellm_install.py) after install or container start.

## Network

- Bind the proxy to **localhost** or a **private subnet** only (see `127.0.0.1:4000` in `docker-compose.yml`).
- Reach the proxy via VPN, private link, or an ingress with **mTLS / IP allowlisting**—not the public internet without controls.

## IAM and secrets

- Use a dedicated **IAM role** with least privilege (`bedrock:InvokeModel` and required Converse actions for your model).
- Prefer **instance/task roles** over long-lived access keys on the proxy host.
- Set a strong `LITELLM_MASTER_KEY`; give ThemeFinder a **virtual key** or the master key only in a secure secret store.
- ThemeFinder clients need `LLM_GATEWAY_URL` and `LITELLM_API_KEY` only—not AWS keys—when the proxy performs Bedrock calls.

## Egress

- Where possible, **allowlist outbound** traffic to Bedrock endpoints for your region to limit exfiltration if the proxy were abused.

## Data and logging

- Disable or minimise proxy request logging in production if responses contain personal or sensitive consultation data.
- Align retention with your organisation’s data-handling / DPIA requirements.

## Incident response

If a compromised LiteLLM build ran on a host (`litellm==1.107.0` or matching Docker digest from the incident post):

1. Rebuild venv/images from scratch.
2. Rotate **IAM role credentials**, `LITELLM_MASTER_KEY`, virtual keys, and any secret present in that environment.
3. Review CloudTrail for unusual `bedrock:*` or `sts:GetCallerIdentity` activity.

## Enterprise LiteLLM

If you use a **licensed Enterprise** proxy, stay on patched releases ([GHSA-w4c7-34wj-hqm8](https://github.com/BerriAI/litellm/security/advisories/GHSA-w4c7-34wj-hqm8)). OSS-only deployments without Enterprise are not on that advisory’s code path.
