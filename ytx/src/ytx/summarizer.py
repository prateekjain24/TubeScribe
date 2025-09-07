from __future__ import annotations

"""Chapter/text summarization via Gemini (optional).

Provides a small wrapper to summarize text snippets, used for per-chapter
summaries when requested by the CLI.
"""

from typing import Optional, List, Dict, Any

from .engines.cloud_base import CloudEngineBase
from dotenv import load_dotenv
from .engines.gemini_engine import _resolve_model_name  # reuse model selection


from .errors import YTXError


class SummarizerError(YTXError):
    def __init__(self, message: str):
        super().__init__(code="SUMMARY", message=message)


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
    # Load .env so local runs pick up keys without exporting environment
    try:
        load_dotenv(override=False)
    except Exception:
        pass
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

    def summarize_structured(self, text: str, *, language: Optional[str] = None, bullets: int = 5, max_tldr: int = 500) -> Dict[str, Any]:
        if not text or not text.strip():
            return {"tldr": "", "bullets": []}
        lang_clause = f" in {language}" if language else ""
        prompt = (
            "You are a concise summarizer. "
            f"Write a TL;DR{lang_clause} under {max_tldr} characters and {bullets} bullet points. "
            "Return STRICT JSON only with keys 'tldr' (string) and 'bullets' (array of strings <= 100 chars)."
        )
        parts = [prompt, text.strip()]
        resp = self._generate_with_retries(self._model, parts, timeout=180, attempts=3)
        payload = getattr(resp, "text", None) or ""
        payload = self._strip_code_fences(payload)
        data: Dict[str, Any]
        try:
            import orjson as _orjson  # type: ignore

            data = _orjson.loads(payload)  # type: ignore[arg-type]
        except Exception:
            try:
                import json as _json

                data = _json.loads(payload)
            except Exception:
                return {"tldr": payload.strip()[:max_tldr], "bullets": []}
        t = str(data.get("tldr") or "").strip()
        bl = data.get("bullets")
        if not isinstance(bl, list):
            bl = []
        bl = [str(x).strip()[:100] for x in bl if str(x).strip()]
        return {"tldr": t[:max_tldr], "bullets": bl[:bullets]}

    def summarize_long(self, text: str, *, language: Optional[str] = None, bullets: int = 5, max_tldr: int = 500) -> Dict[str, Any]:
        """Hierarchical summarization for long transcripts using sliding windows.

        Chunks text into ~4000-char windows, summarizes each, then summarizes the
        concatenated per-chunk TLDRs into a final structured summary.
        """
        s = (text or "").strip()
        if not s:
            return {"tldr": "", "bullets": []}
        win = 4000
        if len(s) <= win:
            return self.summarize_structured(s, language=language, bullets=bullets, max_tldr=max_tldr)
        parts: List[str] = []
        start = 0
        while start < len(s):
            end = min(len(s), start + win)
            # slight overlap of 200 chars
            parts.append(s[start:end])
            if end >= len(s):
                break
            start = end - 200
        # Summarize each chunk and combine TLDRs
        tldrs: List[str] = []
        for chunk in parts:
            r = self.summarize_structured(chunk, language=language, bullets=bullets, max_tldr=max_tldr)
            tldrs.append(r.get("tldr", ""))
        combined = "\n".join(x for x in tldrs if x)
        return self.summarize_structured(combined, language=language, bullets=bullets, max_tldr=max_tldr)

    def _strip_code_fences(self, s: str) -> str:
        t = (s or "").strip()
        if t.startswith("```"):
            lines = t.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip().startswith("```"):
                lines = lines[:-1]
            return "\n".join(lines).strip()
        return t


__all__ = ["GeminiSummarizer", "SummarizerError"]
