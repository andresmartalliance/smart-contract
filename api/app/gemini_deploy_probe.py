"""One bounded Gemini diagnosis from the actual Railway Development API runtime.

No contract files, no requests from the user's browser, no secrets or provider
response bodies in logs. Records status/latency only; does not change a model,
retry, publish a workflow, or affect the API healthcheck.
"""
import logging
import time
from typing import Any

import httpx

logger = logging.getLogger("smart_contract.gemini_probe")
MODEL = "gemini-3.8-flash"
BASE_URL = "https://generativelanguage.googleapis.com/v1beta"


def _safe_error_status(response: httpx.Response) -> str:
    try:
        body = response.json()
        candidate = body.get("error", {}).get("status", "")
        if isinstance(candidate, str) and candidate.isupper() and len(candidate) <= 40:
            return candidate
    except (ValueError, AttributeError, TypeError):
        pass
    return ""


async def _request(client: httpx.AsyncClient, phase: str, method: str,
                   url: str, api_key: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
    since = time.monotonic()
    result = {"phase": phase, "model": MODEL, "http": None,
              "state": "UNKNOWN", "elapsed_ms": None}
    try:
        response = await client.request(
            method, url,
            headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
            json=body,
        )
        result["http"] = response.status_code
        result["state"] = "OK" if response.status_code == 200 else (
            _safe_error_status(response) or "HTTP_ERROR"
        )
        if phase == "generation" and response.status_code == 200:
            try:
                candidates = response.json().get("candidates") or []
                has_text = any(str(part.get("text", "")).strip()
                               for candidate in candidates
                               for part in candidate.get("content", {}).get("parts", []))
                result["state"] = "OK_TEXT" if has_text else "EMPTY_RESPONSE"
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
        result["elapsed_ms"] = round((time.monotonic() - since) * 1000)
        # Only sanitized diagnostics. Do not log body, tokens, request URL or key.
        logger.warning("GEMINI_DIAG phase=%s model=%s state=%s http=%s elapsed_ms=%s",
                       result["phase"], result["model"], result["state"],
                       result["http"], result["elapsed_ms"])
    return result


async def run_gemini_deploy_probe(api_key: str) -> list[dict[str, Any]]:
    """Read-only GetModel followed, iff authorized, by one minimal generation."""
    logger.warning("GEMINI_DIAG startup begin model=%s", MODEL)
    timeout = httpx.Timeout(connect=8.0, read=25.0, write=8.0, pool=8.0)
    async with httpx.AsyncClient(timeout=timeout, trust_env=False) as client:
        get_result = await _request(
            client, "model_get", "GET", f"{BASE_URL}/models/{MODEL}", api_key
        )
        results = [get_result]
        if get_result["http"] == 200:
            text_body = {
                "contents": [{"role": "user", "parts": [{"text": "Responde solo OK."}]}],
                "generationConfig": {"maxOutputTokens": 64, "temperature": 0}
            }
            results.append(await _request(
                client, "generation", "POST",
                f"{BASE_URL}/models/{MODEL}:generateContent", api_key,
                body=text_body
            ))
        else:
            logger.warning("GEMINI_DIAG generation_skipped reason=model_get_not_ok")
    logger.warning("GEMINI_DIAG startup end")
    return results
