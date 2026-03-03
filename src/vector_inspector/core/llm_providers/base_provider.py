"""Base interface for LLM providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class LLMModelInfo:
    """Metadata about an active LLM model."""

    name: str
    provider: str
    context_length: int = 4096
    description: str = ""


class LLMProvider(ABC):
    """Abstract base class for LLM providers.

    Concrete providers must be safe to construct even when their backend is not
    installed or running — availability is tested via ``is_available()``.
    Heavy dependencies must be lazy-loaded inside methods so that importing
    this module does not affect startup time.
    """

    @abstractmethod
    def generate(self, prompt: str, **opts) -> str:
        """Generate a completion from the given prompt.

        Args:
            prompt: Input prompt string.
            **opts: Optional overrides — ``temperature`` (float),
                    ``max_tokens`` (int).

        Returns:
            Generated text response as a plain string.

        Raises:
            RuntimeError: If the provider is unavailable or the request fails.
        """

    @abstractmethod
    def is_available(self) -> bool:
        """Return True if this provider is operational right now.

        Must complete quickly (< 3 s) — it is called during auto-detection
        at settings-open time.
        """

    @abstractmethod
    def get_model_name(self) -> str:
        """Return the active model identifier string."""

    @abstractmethod
    def get_provider_name(self) -> str:
        """Return the provider type identifier, e.g. ``'llama-cpp'``, ``'ollama'``."""

    def get_info(self) -> LLMModelInfo:
        """Return structured metadata about the active model."""
        return LLMModelInfo(
            name=self.get_model_name(),
            provider=self.get_provider_name(),
        )
