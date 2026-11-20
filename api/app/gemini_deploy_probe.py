"""Temporary bounded Gemini API candidate diagnosis from Railway Development.

No user documents; no credentials, payloads or response bodies are logged.
Maximum two tiny inference calls across Flash candidates, no retries.
"""
import logging
import time
from typing import Any

import httpx

logger = logging.getLogger("smart_contract.gemini_probe")
MODELS = ("gemini-3.5-flash", "gemini-3.5-flash-lite")
BASE_URL = "https://generativelanguage.googleapis.com/v1beta"


def _safe_error_status(response: httpx.Response) -> str:
    try:
        candidate = response.json().get("error", {}).get("status", "")
        if isinstance(candidate, str) and candidate.isupper() and len(candidate) <= 40:
            return candidate
    except (ValueError, AttributeError, TypeError):
        pass
    return ""


async def _probe(client: httpx.AsyncClient, api_key: str, model: str,
                 phase: str) -> dict[str, Any]:
    result = {"model": model, "phase": phase, "http": None, "state": "UNKNOWN", "elapsed_ms": 0}
    start = time.monotonic()
    if phase == "model_get":
        method = "GET"
        url = f"{BASE_URL}/models/{model}"
        payload = None
    else:
        method = "POST"
        url = f"{BASE_URL}/models/{model}:generateContent"
        payload = {
            "contents": [{"role": "user", "parts": [{"text": "Responde solo OK."}]}],
            "generationConfig": {"temperature": 0, "maxOutputTokens": 64}
        }
    try:
        response = await client.request(
            method, url,
            headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
            json=payload,
        )
        result["http"] = response.status_code
        result["state"] = "OK" if response.status_code == 200 else (
            _safe_error_status(response) or "HTTP_ERROR"
        )
        if phase == "generation" and response.status_code == 200:
            try:
                candidates = response.json().get("candidates") or []
                texts = [part.get("text", "") for candidate in candidates
                         for part in candidate.get("content", {}).get("parts", [])
                         if isinstance(part, dict)]
                result["state"] = "OK_TEXT" if any(str(t).strip() for t in texts) else "EMPTY_RESPONSE"
            except (ValueError, AttributeError, TypeError):
                result["state"] = "INVALID_RESPONSE"
    except httpx.ConnectTimeout:
        result["state"] = "CONNECT_TIMEOUT"
    except httpx.ReadTimeout:
        result["state"] = "READ_TIMEOUT"
    except httpx.WriteTimeout:
        result["state"] = "WRITE_TIMEOUT"
    except httpx.ConnectError:
        result["state"] = "CONNECT_ERROR"
    except httpx.RequestError:
        result["state"] = "TRANSPORT_ERROR"
    finally:
        result["elapsed_ms"] = round((time.monotonic() - start) * 1000)
        logger.warning("GEMINI_DIAG phase=%s model=%s state=%s http=%s elapsed_ms=%s",
                       phase, model, result["state"], result["http"], result["elapsed_ms"])
    return result


async def run_gemini_deploy_probe(api_key: str) -> list[dict[str, Any]]:
    logger.warning("GEMINI_DIAG candidates begin")
    timeout = httpx.Timeout(connect=8.0, read=25.0, write=8.0, pool=8.0)
    results: list[dict[str, Any]] = []
    async with httpx.AsyncClient(timeout=timeout, trust_env=False) as client:
        for model in MODELS:
            meta = await _probe(client, api_key, model, "model_get")
            results.append(meta)
            if meta["http"] != 200:
                continue
            generated = await _probe(client, api_key, model, "generation")
            results.append(generated)
            if generated["state"] == "OK_TEXT":
                logger.warning("GEMINI_DIAG candidate_verified model=%s", model)
                break
    logger.warning("GEMINI_DIAG candidates end")
    return results
