from __future__ import annotations

"""Chapter/text summarization via Gemini (optional).

Provides a small wrapper to summarize text snippets, used for per-chapter
summaries when requested by the CLI.
"""

from typing import Optional

from .engines.cloud_base import CloudEngineBase
from .engines.gemini_engine import _resolve_model_name  # reuse model selection


class SummarizerError(RuntimeError):
    pass


def _load_api_key() -> str:
    import os

    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        raise SummarizerError(
            "Gemini API key not found. Set GEMINI_API_KEY (or GOOGLE_API_KEY) in your environment/.env"
        )
    if not key.startswith("AIza") or len(key) < 24:
        raise SummarizerError("Invalid Gemini API key format; please verify your GEMINI_API_KEY")
    return key


def _ensure_client() -> None:
    try:
        import google.generativeai as genai  # type: ignore

        genai.configure(api_key=_load_api_key())
    except ImportError as e:
        raise SummarizerError(
            "google-generativeai is not installed. Install it via 'uv add google-generativeai'"
        ) from e
    except Exception as e:
        raise SummarizerError(f"Failed to configure Gemini client: {e}") from e


class GeminiSummarizer(CloudEngineBase):
    def __init__(self, model: str = "gemini-2.5-flash") -> None:
        _ensure_client()
        self.model_name = _resolve_model_name(model)
        import google.generativeai as genai  # type: ignore

        self._model = genai.GenerativeModel(self.model_name)  # type: ignore[attr-defined]

    def summarize(self, text: str, *, language: Optional[str] = None, max_chars: int = 500) -> str:
        if not text or not text.strip():
            return ""
        # Build concise prompt
        lang_clause = f" in {language}" if language else ""
        prompt = (
            "Summarize the following transcript concisely" + lang_clause + ". "
            f"Return a plain text summary under {max_chars} characters, no headings or bullets."
        )
        parts = [prompt, text.strip()]
        resp = self._generate_with_retries(self._model, parts, timeout=120, attempts=3)
        summary = getattr(resp, "text", None) or ""
        return summary.strip()


__all__ = ["GeminiSummarizer", "SummarizerError"]

