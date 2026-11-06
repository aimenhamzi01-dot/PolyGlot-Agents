# Production API deployment

This repository provides a reference deployment for a trained PolyGlot adapter:

```text
client -> FastAPI gateway:8080 -> private vLLM:8000 -> base model + static LoRA adapter
```

The model ID and adapter path are deliberately supplied through environment variables. Do not deploy until the adapter was trained against the exact base model named by `BASE_MODEL`.

## Prerequisites

- A Linux host with Docker, Docker Compose, NVIDIA Container Toolkit and a compatible NVIDIA GPU.
- The exact base model used for training.
- A reviewed LoRA output directory containing `adapter_config.json` and `adapter_model.safetensors`.
- A Hugging Face token only when the base model is gated or private.

## Start

```bash
cp .env.production.example .env.production
# Edit .env.production. Use long random API keys and the real base model.
docker compose --env-file .env.production -f docker-compose.production.yml config
docker compose --env-file .env.production -f docker-compose.production.yml up -d --build
```

The vLLM port is internal to the Compose network. Only the gateway is published on `GATEWAY_PORT`.

## Health checks and request

```bash
curl http://localhost:8080/healthz
curl http://localhost:8080/readyz
curl http://localhost:8080/v1/chat/completions \
  -H "Authorization: Bearer $GATEWAY_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "مرحبا، كيف يمكنكم مساعدتي؟"}],
    "temperature": 0.2,
    "max_tokens": 256
  }'
```

The gateway exposes only the configured `VLLM_MODEL_NAME`; clients cannot select arbitrary upstream models. Streaming is forwarded when `"stream": true`. `/readyz` checks the private vLLM health endpoint.

## Security requirements before public exposure

- Put TLS and a WAF/API gateway in front of port 8080; do not expose vLLM directly.
- Store `.env.production` in a secret manager and rotate both API keys.
- Add a real per-client rate limiter and request quotas before multi-tenant use.
- Redact prompts and completions from application logs unless the user has consented.
- Restrict container egress and filesystem mounts; the model must not receive tool credentials.
- Keep tool execution behind a separate policy service. The LLM may propose a structured action, but it must not directly issue refunds, modify orders or access customer records.
- Pin the vLLM image digest and base-model revision for reproducibility instead of using `latest` in a controlled production release.
- Run load tests, Arabic benchmark regression tests, prompt-injection tests and a rollback drill before serving real traffic.

## LoRA and model identity

The Compose file serves a static adapter with vLLM's `--enable-lora` and `--lora-modules`. Keep the following artifacts together in the release record:

```text
base model identifier + revision
adapter directory + hash
training_manifest.json
source manifest and licenses
benchmark results
```

If the serving engine or platform cannot load PEFT adapters directly, merge the adapter into a copy of the exact base model with `merge_and_unload()`, then serve the merged directory. Keep the unmerged adapter for rollback and reproducibility.
