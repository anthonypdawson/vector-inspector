"""LLM provider backed by a locally running Ollama server."""

from __future__ import annotations

import json
import urllib.request
from typing import Optional

from vector_inspector.core.logging import log_error, log_info

from .base_provider import LLMProvider

DEFAULT_OLLAMA_URL = "http://localhost:11434"
DEFAULT_OLLAMA_MODEL = "llama3.2"

# Short timeout for the availability probe so auto-detection doesn't hang.
_AVAILABILITY_TIMEOUT = 2


class OllamaProvider(LLMProvider):
    """LLM provider that calls a locally running Ollama server via its REST API.

    Ollama is detected and used opportunistically during auto-detection — if
    the server is already running the user gets it for free with no config.
    """

    def __init__(
        self,
        base_url: str = DEFAULT_OLLAMA_URL,
        model: str = DEFAULT_OLLAMA_MODEL,
        context_length: int = 4096,
        temperature: float = 0.1,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._context_length = context_length
        self._temperature = temperature

    def is_available(self) -> bool:
        try:
            req = urllib.request.Request(
                f"{self._base_url}/api/tags",
                method="GET",
                headers={"Accept": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=_AVAILABILITY_TIMEOUT) as resp:
                return resp.status == 200
        except Exception:
            return False

    def generate(self, prompt: str, **opts) -> str:
        payload = json.dumps(
            {
                "model": self._model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": opts.get("temperature", self._temperature),
                    "num_ctx": self._context_length,
                },
            }
        ).encode()

        req = urllib.request.Request(
            f"{self._base_url}/api/generate",
            data=payload,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read())
                return data.get("response", "").strip()
        except Exception as exc:
            log_error("Ollama generate failed: %s", exc)
            raise

    def get_model_name(self) -> str:
        return self._model

    def get_provider_name(self) -> str:
        return "ollama"
