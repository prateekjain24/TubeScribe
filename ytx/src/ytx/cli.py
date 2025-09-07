from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

import typer
from rich.console import Console
from .logging import configure_logging
from .downloader import extract_video_id, fetch_metadata, download_audio
from .audio import normalize_wav
from .config import load_config
from .engines.whisper_engine import WhisperEngine
from .exporters.manager import parse_formats, export_all
from .models import TranscriptDoc

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

    outdir = output_dir or Path.cwd()
    cfg = load_config(engine=engine, model=model)

    # Stage 1: metadata
    with console.status("[bold blue]Fetching metadata…", spinner="dots"):
        meta = fetch_metadata(url)

    # Stage 2: download audio
    with console.status("[bold green]Downloading audio…", spinner="dots"):
        audio_path = download_audio(meta, outdir)

    # Stage 3: normalize to WAV
    with console.status("[bold green]Normalizing audio…", spinner="dots"):
        wav_path = normalize_wav(audio_path, outdir / f"{meta.id}.wav")

    # Stage 4: transcribe (progress bar)
    eng = WhisperEngine()
    from rich.progress import Progress, BarColumn, TimeRemainingColumn, TextColumn

    console.print(f"[bold]Transcribing[/]: {meta.title or meta.id} ({cfg.model})")
    with Progress(TextColumn("{task.description}"), BarColumn(), TimeRemainingColumn()) as progress:
        task = progress.add_task("Transcribing", total=1.0)

        def on_prog(r: float) -> None:
            progress.update(task, completed=max(0.0, min(1.0, r)))

        segments = eng.transcribe(wav_path, config=cfg, on_progress=on_prog)

    # Optional language detection if not provided
    language = cfg.language or eng.detect_language(wav_path, config=cfg)

    # Stage 5: export
    doc = TranscriptDoc(
        video_id=meta.id,
        source_url=meta.url,
        title=meta.title,
        duration=meta.duration,
        language=language,
        engine=cfg.engine,
        model=cfg.model,
        segments=segments,
    )
    written = export_all(doc, outdir, parse_formats("json,srt"))
    console.print("[green]Done[/]: " + ", ".join(p.name for p in written))


# CLI-010: Cache command group (stubs)
cache_app = typer.Typer(help="Manage local cache (stubs)")


@cache_app.command("ls")
def cache_ls() -> None:
    """List cached artifacts (stub)."""
    console.print("[dim]Cache listing not implemented yet.[/]")


@cache_app.command("clear")
def cache_clear(confirm: bool = typer.Option(False, "--yes", help="Confirm deletion")) -> None:
    """Clear cached artifacts (stub)."""
    if not confirm:
        console.print("[yellow]Refusing to clear cache without --yes[/]")
        raise typer.Exit(code=1)
    console.print("[dim]Cache clear not implemented yet.[/]")


app.add_typer(cache_app, name="cache")


if __name__ == "__main__":
    try:
        app()
    except KeyboardInterrupt:
        console.print("[yellow]Aborted by user[/]")
        raise SystemExit(130)
