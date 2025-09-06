from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

import typer
from rich.console import Console
from .logging import configure_logging
from .downloader import extract_video_id

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


@app.command()
def transcribe(
    url: str = typer.Argument(..., help="YouTube URL to transcribe"),
    engine: str = typer.Option("whisper", "--engine", help="Transcription engine (whisper)"),
    model: str = typer.Option("small", "--model", help="Model name for the selected engine"),
    output_dir: Path | None = typer.Option(
        None,
        "--output-dir",
        dir_okay=True,
        file_okay=False,
        writable=True,
        help="Directory to write outputs (must exist)",
    ),
) -> None:
    """Transcribe a YouTube video (stub)."""
    # CLI-008: Parameter validation
    vid = extract_video_id(url)
    if not vid:
        raise typer.BadParameter("Invalid YouTube URL or video ID", param_hint=["url"])
    allowed_engines = {"whisper"}
    if engine not in allowed_engines:
        raise typer.BadParameter("Unsupported engine (supported: whisper)", param_hint=["engine"])
    if output_dir is not None and not output_dir.exists():
        raise typer.BadParameter("Output directory does not exist", param_hint=["output-dir"])

    # Stub implementation for CLI-006; wiring happens in later tickets.
    console.print(f"[bold]Transcribe[/]: id={vid} engine={engine} model={model}")
    if output_dir:
        console.print(f"Output dir: {output_dir}")


if __name__ == "__main__":
    try:
        app()
    except KeyboardInterrupt:
        console.print("[yellow]Aborted by user[/]")
        raise SystemExit(130)
