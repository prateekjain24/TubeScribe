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
from .cache import (
    artifact_paths_for,
    artifacts_exist,
    read_transcript_doc,
    build_meta_payload,
    write_meta,
    scan_cache,
    clear_cache as cache_clear_func,
    cache_statistics,
    expire_cache,
    get_ttl_seconds_from_env,
)

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
    # Optional: clean old cache entries if TTL is configured via env
    ttl = get_ttl_seconds_from_env()
    if ttl:
        removed = expire_cache(ttl)
        if removed:
            console.print(f"[dim]Expired {len(removed)} cache entrie(s) older than TTL[/]")


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
    engine: str = typer.Option(
        "whisper",
        "--engine",
        help="Transcription engine (whisper|whispercpp)",
    ),
    model: str = typer.Option("small", "--model", help="Model name for the selected engine"),
    engine_opts: str | None = typer.Option(
        None,
        "--engine-opts",
        help="JSON for provider-specific options (e.g., '{"utterances":true}')",
    ),
    timestamps: str = typer.Option(
        "native",
        "--timestamps",
        help="Timestamp policy: native|chunked|none",
    ),
    output_dir: Path | None = typer.Option(
        None,
        "--output-dir",
        dir_okay=True,
        file_okay=False,
        writable=True,
        help="Directory to write outputs (must exist)",
    ),
    overwrite: bool = typer.Option(False, "--overwrite", "-f", help="Ignore cache and reprocess"),
    fallback: bool = typer.Option(
        True,
        "--fallback",
        help="When using Gemini, fallback to Whisper on errors",
    ),
) -> None:
    """Transcribe a YouTube video (stub)."""
    # CLI-008: Parameter validation
    vid = extract_video_id(url)
    if not vid:
        raise typer.BadParameter("Invalid YouTube URL or video ID", param_hint=["url"])
    allowed_engines = {"whisper", "whispercpp", "gemini"}
    if engine not in allowed_engines:
        raise typer.BadParameter("Unsupported engine (supported: whisper)", param_hint=["engine"])
    if output_dir is not None and not output_dir.exists():
        raise typer.BadParameter("Output directory does not exist", param_hint=["output-dir"])

    # Parse engine_opts JSON if provided
    opts: dict = {}
    if engine_opts:
        try:
            import orjson as _orjson  # type: ignore

            opts = _orjson.loads(engine_opts)
            if not isinstance(opts, dict):
                raise ValueError("engine-opts must be a JSON object")
        except Exception:
            import json as _json

            try:
                opts = _json.loads(engine_opts)
                if not isinstance(opts, dict):
                    raise ValueError
            except Exception:
                raise typer.BadParameter("Invalid JSON for --engine-opts", param_hint=["--engine-opts"])
    if timestamps not in {"native", "chunked", "none"}:
        raise typer.BadParameter("--timestamps must be one of native|chunked|none", param_hint=["--timestamps"])
    cfg = load_config(engine=engine, model=model, engine_options=opts, timestamp_policy=timestamps)
    # Prepare artifact paths for this video/config
    paths = artifact_paths_for(video_id=vid, config=cfg, create=False)

    # If cache exists and not overwriting, use it
    if not overwrite and artifacts_exist(paths):
        try:
            doc = read_transcript_doc(paths)
            console.print(f"[green]Cache hit[/]: {paths.dir}")
            if output_dir:
                written = export_all(doc, output_dir, parse_formats("json,srt"))
                console.print("[green]Done[/]: " + ", ".join(p.name for p in written))
            else:
                console.print("[dim]Artifacts available at[/]: " + str(paths.dir))
            return
        except Exception as e:
            console.print(f"[yellow]Cache exists but failed to load: {e}. Reprocessing…[/]")

    # No valid cache (or overwrite). Ensure artifact directory exists for writes.
    paths = artifact_paths_for(video_id=vid, config=cfg, create=True)
    outdir = paths.dir  # write primary outputs into the cache directory

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
    # Choose engine (prefer whispercpp for Metal if requested)
    if engine == "gemini":
        from .engines.gemini_engine import GeminiEngine

        eng = GeminiEngine()
    elif engine == "whispercpp" or (engine == "whisper" and cfg.device == "metal"):
        try:
            from .engines.whispercpp_engine import WhisperCppEngine

            eng = WhisperCppEngine()
        except Exception as e:
            console.print(
                "[yellow]whisper.cpp not available; falling back to faster-whisper CPU[/]"
            )
            eng = WhisperEngine()
    else:
        eng = WhisperEngine()
    from rich.progress import Progress, BarColumn, TimeRemainingColumn, TextColumn

    console.print(f"[bold]Transcribing[/]: {meta.title or meta.id} ({cfg.model})")
    with Progress(TextColumn("{task.description}"), BarColumn(), TimeRemainingColumn()) as progress:
        task = progress.add_task("Transcribing", total=1.0)

        def on_prog(r: float) -> None:
            progress.update(task, completed=max(0.0, min(1.0, r)))

        used_cfg = cfg
        used_engine_name = engine
        engine_for_lang = eng
        try:
            segments = eng.transcribe(wav_path, config=cfg, on_progress=on_prog)
        except Exception as e:
            if engine == "gemini" and fallback:
                console.print(f"[yellow]Gemini failed ({e}); falling back to Whisper[/]")
                # Choose a reasonable Whisper model if the provided model is not a Whisper preset
                whisper_presets = {"tiny","tiny.en","base","base.en","small","small.en","medium","medium.en","large-v1","large-v2","large-v3","large-v3-turbo"}
                whisper_model = model if model in whisper_presets else "small"
                used_cfg = load_config(engine="whisper", model=whisper_model)
                used_engine_name = "whisper"
                whisper_eng = WhisperEngine()
                engine_for_lang = whisper_eng
                segments = whisper_eng.transcribe(wav_path, config=used_cfg, on_progress=on_prog)
            else:
                raise

    # Optional language detection if not provided
    language = used_cfg.language or engine_for_lang.detect_language(wav_path, config=used_cfg)

    # Stage 5: export
    doc = TranscriptDoc(
        video_id=meta.id,
        source_url=meta.url,
        title=meta.title,
        duration=meta.duration,
        language=language,
        engine=used_engine_name,
        model=used_cfg.model,
        segments=segments,
    )
    # Export into cache directory (based on the engine actually used) and write meta
    final_paths = artifact_paths_for(video_id=meta.id, config=used_cfg, create=True)
    outdir_final = final_paths.dir
    written = export_all(doc, outdir_final, parse_formats("json,srt"))
    write_meta(final_paths, build_meta_payload(video_id=meta.id, config=used_cfg, source=meta, provider=used_engine_name))
    console.print("[green]Done[/]: " + ", ".join(p.name for p in written))
    # If user requested an explicit output_dir different from cache dir, also write there
    if output_dir and output_dir.resolve() != outdir_final.resolve():
        copied = export_all(doc, output_dir, parse_formats("json,srt"))
        console.print("[dim]Also wrote[/]: " + ", ".join(p.name for p in copied))


# Cache command group
cache_app = typer.Typer(help="Manage local cache")


@cache_app.command("ls")
def cache_ls() -> None:
    """List cached transcripts with title, date, and size."""
    from rich.table import Table
    entries = scan_cache()
    if not entries:
        console.print("[dim]No cached transcripts found.[/]")
        return
    table = Table(title="ytx cache", show_lines=False)
    table.add_column("Video ID", no_wrap=True)
    table.add_column("Engine/Model", no_wrap=True)
    table.add_column("Created", no_wrap=True)
    table.add_column("Size", justify="right")
    table.add_column("Title")
    def _fmt_size(n: int) -> str:
        for unit in ["B","KB","MB","GB","TB"]:
            if n < 1024 or unit == "TB":
                return f"{n:.1f} {unit}" if unit != "B" else f"{n} B"
            n /= 1024.0
        return f"{int(n)} B"
    for e in entries:
        created = e.created_at.isoformat().replace("+00:00","Z") if e.created_at else "—"
        table.add_row(e.video_id, f"{e.engine}/{e.model}", created, _fmt_size(e.size_bytes), e.title or "")
    console.print(table)


@cache_app.command("clear")
def cache_clear(
    confirm: bool = typer.Option(False, "--yes", help="Confirm deletion"),
    video_id: str | None = typer.Option(None, "--video-id", help="Clear cache for a specific video id"),
) -> None:
    """Clear cached artifacts (all or a specific video)."""
    if not confirm:
        console.print("[yellow]Refusing to clear cache without --yes[/]")
        raise typer.Exit(code=1)
    removed, freed = cache_clear_func(video_id=video_id)
    console.print(f"[green]Cleared[/]: {removed} item(s), freed {freed} bytes")


@cache_app.command("stats")
def cache_stats() -> None:
    """Show cache statistics (entries, unique videos, total size)."""
    s = cache_statistics()
    console.print(
        f"Entries: {s['entries']} | Unique videos: {s['unique_videos']} | Total size: {s['total_size_bytes']} bytes"
    )


app.add_typer(cache_app, name="cache")


if __name__ == "__main__":
    try:
        app()
    except KeyboardInterrupt:
        console.print("[yellow]Aborted by user[/]")
        raise SystemExit(130)
