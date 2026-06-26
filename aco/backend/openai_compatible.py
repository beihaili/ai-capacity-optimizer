"""OpenAI-compatible provider calls."""

from __future__ import annotations

import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


INTERNAL_REQUEST_KEYS = {
    "aco_policy",
    "debug",
    "estimated_tokens",
    "live",
    "policy",
    "prompt",
}


class ProviderCallError(Exception):
    """A provider call failed in a way the gateway can report or retry."""

    def __init__(self, message: str, *, code: str = "provider_error", status: int | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status = status

    def to_dict(self) -> dict:
        payload = {"message": self.message, "code": self.code}
        if self.status is not None:
            payload["status"] = self.status
        return payload


def provider_is_live_capable(provider: dict) -> bool:
    return bool(provider.get("base_url") and provider.get("api_key_env"))


def build_chat_completions_url(base_url: str) -> str:
    return base_url.rstrip("/") + "/chat/completions"


def build_openai_payload(provider: dict, payload: dict) -> dict:
    request_payload = {
        key: value
        for key, value in payload.items()
        if key not in INTERNAL_REQUEST_KEYS
    }
    if "messages" not in request_payload:
        request_payload["messages"] = [{"role": "user", "content": str(payload.get("prompt", ""))}]
    request_payload["model"] = provider["model"]
    request_payload["stream"] = False
    return request_payload


def call_openai_compatible(provider: dict, payload: dict) -> dict:
    base_url = provider.get("base_url")
    api_key_env = provider.get("api_key_env")
    if not base_url or not api_key_env:
        raise ProviderCallError(
            "provider is missing base_url or api_key_env",
            code="missing_provider_config",
        )

    api_key = os.getenv(str(api_key_env))
    if not api_key:
        raise ProviderCallError(
            f"environment variable {api_key_env} is not set",
            code="missing_api_key",
        )

    request_body = json.dumps(build_openai_payload(provider, payload)).encode("utf-8")
    request = Request(
        build_chat_completions_url(str(base_url)),
        data=request_body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    timeout = float(provider.get("timeout_seconds") or 30.0)

    try:
        with urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        code = "auth_error" if exc.code in (401, 403) else "provider_http_error"
        raise ProviderCallError(detail or exc.reason, code=code, status=exc.code) from exc
    except URLError as exc:
        raise ProviderCallError(str(exc.reason), code="provider_connection_error") from exc
    except TimeoutError as exc:
        raise ProviderCallError("provider request timed out", code="provider_timeout") from exc

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ProviderCallError("provider returned non-JSON response", code="provider_bad_json") from exc
    if not isinstance(parsed, dict):
        raise ProviderCallError("provider response must be a JSON object", code="provider_bad_json")
    parsed.setdefault("model", provider["model"])
    return parsed
