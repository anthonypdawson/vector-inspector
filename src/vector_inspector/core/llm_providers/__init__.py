"""LLM provider layer for Vector Inspector.

Provides a pluggable interface for text generation backed by:
- llama-cpp-python (in-process, zero-setup default)
- Ollama (local server, used opportunistically when running)
- OpenAI-compatible REST API (cloud or local proxy)

Auto-detection order: user-configured → Ollama → llama-cpp.
"""

from .base_provider import LLMModelInfo, LLMProvider
from .provider_factory import (
    AUTO,
    LLAMA_CPP,
    OLLAMA,
    OPENAI_COMPATIBLE,
    PROVIDER_TYPES,
    LLMProviderFactory,
    LLMProviderInstance,
)

__all__ = [
    "AUTO",
    "LLAMA_CPP",
    "OLLAMA",
    "OPENAI_COMPATIBLE",
    "PROVIDER_TYPES",
    "LLMModelInfo",
    "LLMProvider",
    "LLMProviderFactory",
    "LLMProviderInstance",
]
