"""LLM provider for OpenAI-compatible REST APIs.

Supports OpenAI, LM Studio, Groq, LocalAI, or any server that implements
the ``/v1/chat/completions`` endpoint.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request

from vector_inspector.core.logging import log_error

from .base_provider import LLMProvider


class OpenAICompatibleProvider(LLMProvider):
    """Provider for APIs that implement the OpenAI chat-completions interface."""

    def __init__(
        self,
        base_url: str,
        model: str,
        api_key: str = "",
        context_length: int = 4096,
        temperature: float = 0.1,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._api_key = api_key
        self._context_length = context_length
        self._temperature = temperature

    def _headers(self) -> dict[str, str]:
        headers: dict[str, str] = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        return headers

    def is_available(self) -> bool:
        if not self._base_url or not self._model:
            return False
        try:
            req = urllib.request.Request(
                f"{self._base_url}/models",
                method="GET",
                headers=self._headers(),
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status == 200
        except Exception:
            return False

    def generate(self, prompt: str, **opts) -> str:
        payload = json.dumps(
            {
                "model": self._model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": opts.get("temperature", self._temperature),
                "max_tokens": opts.get("max_tokens", 512),
            }
        ).encode()

        req = urllib.request.Request(
            f"{self._base_url}/chat/completions",
            data=payload,
            method="POST",
            headers=self._headers(),
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read())
                return data["choices"][0]["message"]["content"].strip()
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            log_error("OpenAI-compatible API HTTP %s: %s", exc.code, body[:500])
            raise RuntimeError(f"API returned HTTP {exc.code}: {body[:200]}") from exc
        except Exception as exc:
            log_error("OpenAI-compatible generate failed: %s", exc)
            raise

    def get_model_name(self) -> str:
        return self._model

    def get_provider_name(self) -> str:
        return "openai-compatible"
