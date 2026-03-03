"""In-process LLM provider using llama-cpp-python."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from vector_inspector.core.logging import log_error, log_info

from .base_provider import LLMProvider

# Default model: Phi-3-mini-4k Q4_K_M — ~2.4 GB, good CPU quality/size balance.
DEFAULT_MODEL_FILENAME = "Phi-3-mini-4k-instruct-Q4_K_M.gguf"
DEFAULT_MODEL_HF_URL = (
    "https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf"
    "/resolve/main/Phi-3-mini-4k-instruct-Q4_K_M.gguf"
)


# ---------------------------------------------------------------------------
# Cache helpers
# ---------------------------------------------------------------------------


def get_llm_cache_dir() -> Path:
    """Return the LLM GGUF model cache directory, creating it if needed.

    Honours the ``llm.cache_dir`` setting when set; otherwise uses
    ``~/.vector-inspector/llm_cache``.
    """
    try:
        from vector_inspector.services.settings_service import SettingsService

        custom = SettingsService().get("llm.cache_dir")
        if custom:
            path = Path(custom)
            path.mkdir(parents=True, exist_ok=True)
            return path
    except Exception:
        pass
    path = Path.home() / ".vector-inspector" / "llm_cache"
    path.mkdir(parents=True, exist_ok=True)
    return path


def list_cached_models() -> list[str]:
    """Return filenames of all GGUF models in the LLM cache directory."""
    cache_dir = get_llm_cache_dir()
    if not cache_dir.exists():
        return []
    return sorted(f.name for f in cache_dir.glob("*.gguf"))


def download_default_model(progress_callback=None) -> Path:
    """Download the default Phi-3-mini GGUF model to the LLM cache.

    Args:
        progress_callback: Optional ``callable(downloaded_bytes: int,
            total_bytes: int)`` called periodically during download.

    Returns:
        Path to the downloaded (or already-cached) model file.
    """
    import urllib.request

    dest = get_llm_cache_dir() / DEFAULT_MODEL_FILENAME
    if dest.exists():
        log_info("Default LLM model already cached: %s", dest)
        return dest

    def _report(block_num: int, block_size: int, total_size: int) -> None:
        if progress_callback is not None:
            downloaded = min(block_num * block_size, total_size)
            progress_callback(downloaded, total_size)

    log_info("Downloading default LLM model to %s", dest)
    urllib.request.urlretrieve(DEFAULT_MODEL_HF_URL, str(dest), _report)
    log_info("LLM model download complete: %s", dest)
    return dest


# ---------------------------------------------------------------------------
# Provider
# ---------------------------------------------------------------------------


class LlamaCppProvider(LLMProvider):
    """In-process LLM via ``llama-cpp-python``.

    Requires the ``llama-cpp-python`` package (available on PyPI for
    Windows / macOS / Linux without a C++ toolchain for most platforms).
    GPU layers are used automatically when a compatible device is present;
    falls back to CPU-only inference otherwise.
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        context_length: int = 4096,
        temperature: float = 0.1,
    ) -> None:
        self._model_path = model_path
        self._context_length = context_length
        self._temperature = temperature
        self._llm = None  # lazy-loaded Llama instance

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_model_path(self) -> Optional[Path]:
        """Return the active model path, or None if not resolvable."""
        if self._model_path:
            p = Path(self._model_path)
            return p if p.exists() else None
        candidate = get_llm_cache_dir() / DEFAULT_MODEL_FILENAME
        return candidate if candidate.exists() else None

    def _load_model(self) -> None:
        if self._llm is not None:
            return
        model_path = self._resolve_model_path()
        if model_path is None:
            raise FileNotFoundError(
                f"No LLM model found. Download a GGUF model to {get_llm_cache_dir()} "
                "or set a model path in Settings → LLM."
            )
        try:
            from llama_cpp import Llama  # noqa: PLC0415

            log_info("Loading llama-cpp model: %s", model_path)
            self._llm = Llama(
                model_path=str(model_path),
                n_ctx=self._context_length,
                n_gpu_layers=-1,  # -1 = use all GPU layers available; 0 = CPU only
                verbose=False,
            )
            log_info("llama-cpp model loaded.")
        except Exception as exc:
            log_error("Failed to load llama-cpp model: %s", exc)
            raise

    # ------------------------------------------------------------------
    # LLMProvider interface
    # ------------------------------------------------------------------

    def is_available(self) -> bool:
        try:
            import llama_cpp  # noqa: F401, PLC0415
        except ImportError:
            return False
        return self._resolve_model_path() is not None

    def generate(self, prompt: str, **opts) -> str:
        self._load_model()
        output = self._llm(
            prompt,
            temperature=opts.get("temperature", self._temperature),
            max_tokens=opts.get("max_tokens", 512),
            echo=False,
        )
        return output["choices"][0]["text"].strip()

    def get_model_name(self) -> str:
        p = self._resolve_model_path()
        return p.name if p else DEFAULT_MODEL_FILENAME

    def get_provider_name(self) -> str:
        return "llama-cpp"
