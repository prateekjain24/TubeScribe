from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

import typer
from rich.console import Console
from .logging import configure_logging

app = typer.Typer(
    no_args_is_help=True,
    invoke_without_command=True,
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
def _root(
    verbose: bool = typer.Option(False, "--verbose", help="Enable verbose output"),
    version_flag: bool = typer.Option(
        False,
        "--version",
        "-V",
        is_eager=True,
        help="Show ytx version and exit",
    ),
) -> None:
    """CLI foundation and global options."""
    if version_flag:
        console.print(f"ytx v{_pkg_version()}")
        raise typer.Exit(code=0)
    configure_logging(verbose=verbose)


@app.command()
def version_cmd() -> None:
    """Show version and exit."""
    console.print(f"ytx {_pkg_version()}")


@app.command()
def hello(name: str = "world") -> None:
    """Placeholder command to validate CLI plumbing."""
    console.print(f"Hello, {name}!")


if __name__ == "__main__":
    try:
        app()
    except KeyboardInterrupt:
        console.print("[yellow]Aborted by user[/]")
        raise SystemExit(130)
