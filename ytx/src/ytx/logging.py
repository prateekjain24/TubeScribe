from __future__ import annotations

import logging
from typing import Optional

from rich.console import Console
from rich.logging import RichHandler


console = Console()


def configure_logging(*, verbose: bool = False) -> None:
    """Configure root logging with Rich.

    - INFO level by default; DEBUG when `verbose` is True
    - Uses a single RichHandler; idempotent across repeated calls
    """
    level = logging.DEBUG if verbose else logging.INFO
    root = logging.getLogger()
    # If a RichHandler with our format is present, just adjust level
    for h in root.handlers:
        if isinstance(h, RichHandler):
            root.setLevel(level)
            h.setLevel(level)
            return

    handler = RichHandler(rich_tracebacks=True, show_time=False, show_path=False)
    handler.setLevel(level)
    logging.basicConfig(
        level=level,
        format="%(message)s",
        handlers=[handler],
    )


def get_logger(name: Optional[str] = None) -> logging.Logger:
    return logging.getLogger(name)


__all__ = ["console", "configure_logging", "get_logger"]

