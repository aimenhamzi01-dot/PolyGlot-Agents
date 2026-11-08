"""Production-oriented gateway in front of an internal vLLM OpenAI-compatible server."""
from __future__ import annotations

import os
from typing import Any, Literal

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from serving.tool_registry import available_tool_locales, canonical_tool_locale, get_tool_definitions

VLLM_BASE_URL = os.getenv("VLLM_BASE_URL", "http://vllm:8000").rstrip("/")
GATEWAY_API_KEY = os.getenv("GATEWAY_API_KEY", "")
DEFAULT_MODEL = os.getenv("VLLM_MODEL_NAME", "")
UPSTREAM_API_KEY = os.getenv("VLLM_API_KEY", "")
TIMEOUT_SECONDS = float(os.getenv("UPSTREAM_TIMEOUT_SECONDS", "120"))

app = FastAPI(
    title="PolyGlot Agents Gateway",
    version="0.1.0",
    description="OpenAI-compatible inference gateway. Tool schemas are exposed for model proposals; the gateway never executes tools.",
)


class ChatRequest(BaseModel):
    model: str | None = None
    messages: list[dict[str, Any]] = Field(min_length=1)
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    max_tokens: int = Field(default=256, gt=0, le=4096)
    stream: bool = False
    tools: list[dict[str, Any]] | None = Field(default=None, max_length=32)
    tool_choice: Literal["none", "auto", "required"] | dict[str, Any] | None = None
    parallel_tool_calls: bool | None = None


async def authenticate(authorization: str | None = Header(default=None)) -> None:
    if not GATEWAY_API_KEY:
        raise HTTPException(status_code=503, detail="GATEWAY_API_KEY is not configured")
    expected = f"Bearer {GATEWAY_API_KEY}"
    if authorization != expected:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")


def upstream_headers() -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if UPSTREAM_API_KEY:
        headers["Authorization"] = f"Bearer {UPSTREAM_API_KEY}"
    return headers


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok", "service": "polyglot-gateway"}


@app.get("/readyz")
async def readyz() -> JSONResponse:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{VLLM_BASE_URL}/health", headers=upstream_headers())
        if response.status_code >= 400:
            return JSONResponse({"status": "not_ready", "upstream_status": response.status_code}, status_code=503)
        return JSONResponse({"status": "ready"})
    except httpx.HTTPError as exc:
        return JSONResponse({"status": "not_ready", "error": str(exc)}, status_code=503)


@app.post("/v1/chat/completions")
async def chat_completions(payload: ChatRequest, _: None = Depends(authenticate)):
    model = payload.model or DEFAULT_MODEL
    if not model:
        raise HTTPException(status_code=503, detail="VLLM_MODEL_NAME is not configured")
    if DEFAULT_MODEL and model != DEFAULT_MODEL:
        raise HTTPException(status_code=400, detail="Requested model is not enabled")
    body = payload.model_dump(exclude_none=True)
    body["model"] = model
    try:
        if payload.stream:
            client = httpx.AsyncClient(timeout=None)
            request = client.build_request(
                "POST", f"{VLLM_BASE_URL}/v1/chat/completions", json=body, headers=upstream_headers()
            )
            response = await client.send(request, stream=True)
            if response.status_code >= 400:
                detail = await response.aread()
                await response.aclose()
                await client.aclose()
                raise HTTPException(status_code=response.status_code, detail=detail.decode("utf-8", "replace"))

            async def iterator():
                try:
                    async for chunk in response.aiter_bytes():
                        yield chunk
                finally:
                    await response.aclose()
                    await client.aclose()

            return StreamingResponse(iterator(), status_code=response.status_code, media_type="text/event-stream")

        async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
            response = await client.post(
                f"{VLLM_BASE_URL}/v1/chat/completions", json=body, headers=upstream_headers()
            )
        return JSONResponse(response.json(), status_code=response.status_code)
    except httpx.TimeoutException as exc:
        raise HTTPException(status_code=504, detail="Upstream generation timed out") from exc
    except httpx.ConnectError as exc:
        raise HTTPException(status_code=503, detail="vLLM upstream is unavailable") from exc


@app.get("/v1/models")
async def models(_: None = Depends(authenticate)):
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{VLLM_BASE_URL}/v1/models", headers=upstream_headers())
        return JSONResponse(response.json(), status_code=response.status_code)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=503, detail="vLLM upstream is unavailable") from exc


@app.get("/v1/tools", summary="List agent tool schemas")
def list_tools(
    locale: str = Query(default="en", min_length=2, max_length=16),
    _: None = Depends(authenticate),
) -> dict[str, Any]:
    """Return localized OpenAI function-calling definitions; no tools are executed here."""
    try:
        tools = get_tool_definitions(locale)
    except ValueError as exc:
        supported = ", ".join(available_tool_locales())
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported locale. Supported primary language codes: {supported}",
        ) from exc
    canonical_locale = canonical_tool_locale(locale)
    return {"object": "list", "locale": canonical_locale, "tools": tools}
