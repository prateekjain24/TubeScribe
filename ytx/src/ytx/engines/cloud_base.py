from __future__ import annotations

"""Cloud engine base helpers shared across providers.

Provides retryable request wrapper and basic rate-limit detection. Engines can
override `_is_rate_limit_error` to provide provider-specific checks.
"""

from tenacity import Retrying, stop_after_attempt, wait_random_exponential, retry_if_exception


class CloudEngineBase:
    def _is_rate_limit_error(self, e: Exception) -> bool:  # pragma: no cover - override in engines as needed
        s = str(e).lower()
        return any(x in s for x in ("rate limit", "quota", "too many requests", "429"))

    def _generate_with_retries(self, model, parts, *, timeout: int = 600, attempts: int = 3):  # type: ignore[no-untyped-def]
        def _retry_predicate(exc: Exception) -> bool:
            return self._is_rate_limit_error(exc)

        for attempt in Retrying(
            stop=stop_after_attempt(attempts),
            wait=wait_random_exponential(multiplier=1, max=8),
            retry=retry_if_exception(_retry_predicate),
            reraise=True,
        ):
            with attempt:
                try:
                    return model.generate_content(parts, request_options={"timeout": timeout})  # type: ignore[attr-defined]
                except Exception as e:
                    if not self._is_rate_limit_error(e):
                        raise
                    raise


__all__ = ["CloudEngineBase"]

