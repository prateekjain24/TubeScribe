from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

import typer
from rich.console import Console

app = typer.Typer(
    no_args_is_help=True,
    add_completion=False,
    help="ytx: YouTube transcription CLI (Whisper/Gemini)",
    pretty_exceptions_enable=False,
    pretty_exceptions_show_locals=False,
    pretty_exceptions_short=True,
)
console = Console()


def _pkg_version() -> str:
    try:
        return version("ytx")
    except PackageNotFoundError:
        return "0.1.0"


@app.callback()
def _root(verbose: bool = typer.Option(False, "--verbose", help="Enable verbose output")) -> None:
    """CLI foundation and global options."""
    # Placeholder for global options; rich console is configured per-command.
    _ = verbose


@app.command()
def version_cmd() -> None:
    """Show version and exit."""
    console.print(f"ytx {_pkg_version()}")


@app.command()
def hello(name: str = "world") -> None:
    """Placeholder command to validate CLI plumbing."""
    console.print(f"Hello, {name}!")


if __name__ == "__main__":
    app()
