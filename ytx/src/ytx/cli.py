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
from .exporters.markdown_exporter import MarkdownExporter  # ensure importable for CLI wiring
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
from .chapters import (
    slice_audio_by_chapters,
    process_chapters,
    offset_chapter_segments,
    stitch_chapter_segments,
)
from .errors import write_error_report

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
    # Try distribution names: prefer 'tubescribe' (new dist), fall back to 'ytx'.
    for dist in ("tubescribe", "ytx"):
        try:
            return version(dist)
        except PackageNotFoundError:
            continue
    # Fallback when running from source without installed dist
    return "0.2.1"


@app.callback()
def _root(
    verbose: bool = typer.Option(False, "--verbose", help="Enable verbose output"),
    debug: bool = typer.Option(False, "--debug", help="Enable debug logging and extra diagnostics"),
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
    configure_logging(verbose=verbose or debug)
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
        help='JSON for provider-specific options (e.g., \'{"utterances":true}\')',
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
    by_chapter: bool = typer.Option(
        False,
        "--by-chapter",
        help="Transcribe by chapters when available",
    ),
    parallel_chapters: bool = typer.Option(
        True,
        "--parallel-chapters/--no-parallel-chapters",
        help="Process chapters concurrently when using --by-chapter",
    ),
    chapter_overlap: float = typer.Option(2.0, "--chapter-overlap", help="Seconds of overlap between chapter slices"),
    summarize_chapters: bool = typer.Option(
        False,
        "--summarize-chapters/--no-summarize-chapters",
        help="Generate a short summary per chapter (uses Gemini)",
    ),
    summarize: bool = typer.Option(
        False,
        "--summarize/--no-summarize",
        help="Generate an overall transcript summary (uses Gemini)",
    ),
    max_download_abr_kbps: int | None = typer.Option(
        96,
        "--max-download-abr-kbps",
        help="Cap YouTube audio bitrate (kbps) during download; set 0 to disable",
    ),
    download_extract_audio: bool = typer.Option(
        False,
        "--download-extract-audio/--no-download-extract-audio",
        help="Use yt-dlp to extract to a target audio format during download (extra re-encode)",
    ),
) -> None:
    """Transcribe a YouTube video (stub)."""
    # CLI-008: Parameter validation
    vid = extract_video_id(url)
    if not vid:
        raise typer.BadParameter("Invalid YouTube URL or video ID", param_hint=["url"])
    allowed_engines = {"whisper", "whispercpp", "gemini", "openai", "deepgram", "elevenlabs"}
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
    # Normalize cap: treat <=0 as None
    abr_cap = None if (max_download_abr_kbps is None or max_download_abr_kbps <= 0) else int(max_download_abr_kbps)
    cfg = load_config(
        engine=engine,
        model=model,
        engine_options=opts,
        timestamp_policy=timestamps,
        max_download_abr_kbps=abr_cap,
        download_extract_audio=download_extract_audio,
    )
    # Prepare artifact paths for this video/config
    paths = artifact_paths_for(video_id=vid, config=cfg, create=False)

    # If cache exists and not overwriting, use it (but allow new summary generation)
    if not overwrite and artifacts_exist(paths):
        try:
            doc = read_transcript_doc(paths)
            console.print(f"[green]Cache hit[/]: {paths.dir}")
            # Optional new summary on top of cached artifacts
            if summarize and (getattr(doc, "summary", None) is None):
                from .summarizer import GeminiSummarizer
                from .cache import read_summary, write_summary
                existing = read_summary(paths)
                if existing and isinstance(existing, dict):
                    try:
                        from .models import Summary as SummaryModel

                        doc.summary = SummaryModel.model_validate(existing)
                    except Exception:
                        doc.summary = None
                if doc.summary is None:
                    text = "\n".join(s.text for s in doc.segments if s.text).strip()
                    if text:
                        summarizer = GeminiSummarizer()
                        res = summarizer.summarize_long(text, language=doc.language, bullets=5, max_tldr=500)
                        from .models import Summary as SummaryModel

                        doc.summary = SummaryModel(tldr=res.get("tldr", ""), bullets=list(res.get("bullets", [])))
                        write_summary(paths, doc.summary.model_dump())
                    else:
                        console.print("[yellow]No text content to summarize[/]")
                # Update transcript.json in cache with summary included
                export_all(doc, paths.dir, parse_formats("json"))
            # Write to output_dir if specified
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

    try:
        # Stage 1: metadata
        with console.status("[bold blue]Fetching metadata…", spinner="dots"):
            meta = fetch_metadata(url, timeout=cfg.network_timeout, max_abr_kbps=cfg.max_download_abr_kbps)

        # Stage 2: download audio
        with console.status("[bold green]Downloading audio…", spinner="dots"):
            audio_path = download_audio(
                meta,
                outdir,
                timeout=cfg.download_timeout,
                max_abr_kbps=cfg.max_download_abr_kbps,
                download_extract_audio=cfg.download_extract_audio,
            )

        # Stage 3: normalize to WAV
        with console.status("[bold green]Normalizing audio…", spinner="dots"):
            wav_path = normalize_wav(audio_path, outdir / f"{meta.id}.wav")
    except KeyboardInterrupt:
        report = write_error_report(paths.dir if 'paths' in locals() else Path.cwd(), InterruptError().with_traceback(None) if False else KeyboardInterrupt(), context={"stage": "init", "url": url})
        console.print(f"[yellow]Aborted by user. Error report: {report}[/]")
        raise typer.Exit(code=130)

    # Stage 4: transcribe (progress bar)
    # Choose engine (prefer whispercpp for Metal if requested)
    if engine == "gemini":
        from .engines.gemini_engine import GeminiEngine

        eng = GeminiEngine()
    elif engine == "openai":
        from .engines.openai_engine import OpenAIEngine

        eng = OpenAIEngine()
    elif engine == "deepgram":
        from .engines.deepgram_engine import DeepgramEngine

        eng = DeepgramEngine()
    elif engine == "elevenlabs":
        from .engines.eleven_engine import ElevenLabsEngine

        eng = ElevenLabsEngine()
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
    from rich.progress import Progress, BarColumn, TimeRemainingColumn, TextColumn, TaskProgressColumn

    console.print(f"[bold]Transcribing[/]: {meta.title or meta.id} ({cfg.model})")
    with Progress(TextColumn("{task.description}"), BarColumn(), TaskProgressColumn(), TimeRemainingColumn()) as progress:
        task = progress.add_task("Transcribing", total=1.0)

        def on_prog(r: float) -> None:
            progress.update(task, completed=max(0.0, min(1.0, r)))

        used_cfg = cfg
        used_engine_name = engine
        engine_for_lang = eng
        segments = []
        chapter_results: list[tuple[int, any, list]] | None = None
        chapter_results: list[tuple[int, any, list]] | None = None
        try:
            if by_chapter and (meta.chapters or []):
                # Chapter-aware processing path
                parts = slice_audio_by_chapters(
                    wav_path,
                    meta.chapters or [],
                    out_dir=paths.dir / "chapters",
                    overlap_seconds=chapter_overlap,
                )
                n = len(parts)
                # Build per-chapter progress tasks
                chapter_tasks: dict[int, int] = {}
                for i, ch, _ in parts:
                    title = (ch.title or f"Chapter {i}")
                    chapter_tasks[i] = progress.add_task(f"Ch {i:02d}: {title}", total=1.0)

                from concurrent.futures import ThreadPoolExecutor, as_completed
                import os

                max_workers = min(n, os.cpu_count() or 4) if parallel_chapters else 1
                results: list[tuple[int, any, list]] = []
                def transcribe_one(i_ch_path):
                    i, ch, path = i_ch_path
                    segs = eng.transcribe(path, config=cfg, on_progress=None)
                    return (i, ch, segs)

                completed = 0
                with ThreadPoolExecutor(max_workers=max_workers) as ex:
                    futs = {ex.submit(transcribe_one, item): item[0] for item in parts}
                    for fut in as_completed(futs):
                        i = futs[fut]
                        try:
                            i, ch, segs = fut.result()
                        except Exception as e:
                            # Fallback per chapter not implemented; bubble up
                            raise
                        results.append((i, ch, segs))
                        chapter_results = results
                        completed += 1
                        progress.update(chapter_tasks[i], completed=1.0)
                        progress.update(task, completed=max(0.0, min(1.0, completed / n)))
                # Sort, offset, and stitch
                results.sort(key=lambda t: t[0])
                chapter_results = results
                segments = stitch_chapter_segments(offset_chapter_segments(results))
                # Mark overall complete
                progress.update(task, completed=1.0)
            else:
                # Single-pass transcription
                segments = eng.transcribe(wav_path, config=cfg, on_progress=on_prog)
        except Exception as e:
            if engine == "gemini" and fallback:
                console.print(f"[yellow]Gemini failed ({e}); falling back to Whisper[/]")
                whisper_presets = {"tiny","tiny.en","base","base.en","small","small.en","medium","medium.en","large-v1","large-v2","large-v3","large-v3-turbo"}
                whisper_model = model if model in whisper_presets else "small"
                used_cfg = load_config(engine="whisper", model=whisper_model)
                used_engine_name = "whisper"
                whisper_eng = WhisperEngine()
                engine_for_lang = whisper_eng
                # Retry with whisper (single or chapters)
                if by_chapter and (meta.chapters or []):
                    parts = slice_audio_by_chapters(
                        wav_path,
                        meta.chapters or [],
                        out_dir=paths.dir / "chapters",
                        overlap_seconds=chapter_overlap,
                    )
                    n = len(parts)
                    from concurrent.futures import ThreadPoolExecutor, as_completed
                    import os
                    max_workers = min(n, os.cpu_count() or 4) if parallel_chapters else 1
                    results: list[tuple[int, any, list]] = []
                    def transcribe_one(i_ch_path):
                        i, ch, path = i_ch_path
                        segs = whisper_eng.transcribe(path, config=used_cfg, on_progress=None)
                        return (i, ch, segs)
                    completed = 0
                    with ThreadPoolExecutor(max_workers=max_workers) as ex:
                        futs = {ex.submit(transcribe_one, item): item[0] for item in parts}
                        for fut in as_completed(futs):
                            i = futs[fut]
                            i, ch, segs = fut.result()
                            results.append((i, ch, segs))
                            chapter_results = results
                            completed += 1
                    results.sort(key=lambda t: t[0])
                    chapter_results = results
                    segments = stitch_chapter_segments(offset_chapter_segments(results))
                else:
                    segments = whisper_eng.transcribe(wav_path, config=used_cfg, on_progress=on_prog)
            else:
                # Recovery strategy: write partial results if available and by-chapter was used
                try:
                    if by_chapter and chapter_results:
                        partial_segments = stitch_chapter_segments(offset_chapter_segments(chapter_results))
                        partial_doc = TranscriptDoc(
                            video_id=vid,
                            source_url=url,
                            title=meta.title,
                            duration=meta.duration,
                            language=cfg.language,
                            engine=used_engine_name,
                            model=cfg.model,
                            segments=partial_segments,
                            chapters=meta.chapters,
                        )
                        export_all(partial_doc, paths.dir, parse_formats("json"))
                        console.print("[yellow]Wrote partial transcript due to failure[/]")
                finally:
                    report = write_error_report(paths.dir if 'paths' in locals() else Path.cwd(), e, context={"command": "transcribe", "video_id": vid})
                    console.print(f"[red]Error report written:[/] {report}")
                    raise

    # Optional language detection if not provided
    language = used_cfg.language or engine_for_lang.detect_language(wav_path, config=used_cfg)

    # Optional per-chapter summaries
    chapters_for_doc = meta.chapters
    if summarize_chapters and (meta.chapters or []):
        try:
            from .summarizer import GeminiSummarizer

            summarizer = GeminiSummarizer()
            chapters_for_doc = []
            if by_chapter and chapter_results is not None:
                for i, ch, segs in chapter_results:
                    text = " ".join(s.text for s in segs if s.text).strip()
                    summ = summarizer.summarize(text, language=language, max_chars=500) if text else ""
                    chapters_for_doc.append(type(ch)(title=ch.title, start=ch.start, end=ch.end, summary=summ))
            else:
                # Derive text per chapter from global segments
                for ch in meta.chapters or []:
                    text = " ".join(s.text for s in segments if s.start >= ch.start and s.end <= ch.end).strip()
                    summ = summarizer.summarize(text, language=language, max_chars=500) if text else ""
                    chapters_for_doc.append(type(ch)(title=ch.title, start=ch.start, end=ch.end, summary=summ))
        except Exception as e:
            console.print(f"[yellow]Chapter summaries unavailable: {e}[/]")

    # Optional per-chapter summaries
    # Optional overall summary (generate before export)
    overall_summary = None
    if summarize:
        try:
            from .summarizer import GeminiSummarizer
            summarizer = GeminiSummarizer()
            full_text = "\n".join(s.text for s in segments if s.text).strip()
            if full_text:
                res = summarizer.summarize_long(full_text, language=language, bullets=5, max_tldr=500)
                from .models import Summary as SummaryModel

                overall_summary = SummaryModel(tldr=res.get("tldr", ""), bullets=list(res.get("bullets", [])))
            else:
                console.print("[yellow]No text content to summarize[/]")
        except Exception as e:
            console.print(f"[yellow]Transcript summary unavailable: {e}[/]")

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
        chapters=chapters_for_doc,
        summary=overall_summary,
    )
    # Export into cache directory (based on the engine actually used) and write meta
    final_paths = artifact_paths_for(video_id=meta.id, config=used_cfg, create=True)
    outdir_final = final_paths.dir
    written = export_all(doc, outdir_final, parse_formats("json,srt"))
    if summarize and overall_summary is not None:
        from .cache import write_summary

        write_summary(final_paths, overall_summary.model_dump())
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


# --- Summarization from existing transcript ---
@app.command("summarize-file")
def summarize_file(
    path: Path = typer.Argument(..., exists=True, file_okay=True, dir_okay=False, readable=True, help="Path to transcript JSON (TranscriptDoc)"),
    language: str | None = typer.Option(None, "--language", help="Target language for summary or auto from doc"),
    write: bool = typer.Option(False, "--write", help="Write summary JSON next to input file"),
) -> None:
    """Summarize an existing transcript JSON (TranscriptDoc)."""
    try:
        raw = path.read_text(encoding="utf-8")
    except Exception as e:
        raise typer.BadParameter(f"Failed to read file: {e}")
    try:
        from .models import TranscriptDoc as _TD

        doc = _TD.model_validate_json(raw)
    except Exception:
        import json as _json

        try:
            payload = _json.loads(raw)
            from .models import TranscriptDoc as _TD

            doc = _TD.model_validate(payload)
        except Exception as e:
            raise typer.BadParameter(f"Invalid TranscriptDoc JSON: {e}")
    try:
        from .summarizer import GeminiSummarizer
        summarizer = GeminiSummarizer()
        txt = "\n".join(s.text for s in doc.segments if s.text).strip()
        if not txt:
            console.print("[yellow]No text content to summarize[/]")
            raise typer.Exit(code=1)
        lang = language or doc.language
        console.print("[bold]Summarizing transcript…[/]")
        res = summarizer.summarize_long(txt, language=lang, bullets=5, max_tldr=500)
        from .models import Summary as _Summary

        summ = _Summary(tldr=res.get("tldr", ""), bullets=list(res.get("bullets", [])))
        console.print("\n[bold]TL;DR[/]:\n" + summ.tldr)
        if summ.bullets:
            console.print("\n[bold]Key Points[/]:")
            for b in summ.bullets:
                console.print(f"- {b}")
        if write:
            out = path.with_suffix(".summary.json")
            try:
                from .cache import write_bytes_atomic
                import orjson as _orjson  # type: ignore

                data = _orjson.dumps(summ.model_dump(), option=_orjson.OPT_SORT_KEYS)
            except Exception:
                import json as _json

                data = _json.dumps(summ.model_dump(), sort_keys=True, indent=2).encode("utf-8")
            write_bytes_atomic(out, data)
            console.print(f"\n[green]Wrote summary[/]: {out}")
    except KeyboardInterrupt:
        report = write_error_report(path.parent, KeyboardInterrupt(), context={"command": "summarize-file", "file": str(path)})
        console.print(f"[yellow]Aborted by user. Error report: {report}[/]")
        raise typer.Exit(code=130)
    except Exception as e:
        report = write_error_report(path.parent, e, context={"command": "summarize-file", "file": str(path)})
        console.print(f"[red]Error report written:[/] {report}")
        raise


@app.command("update-check")
def update_check(repo: str = typer.Option("prateekjain24/TubeScribe", "--repo", help="GitHub repo to check")) -> None:
    """Check for the latest release on GitHub and compare with local version."""
    import httpx
    current = _pkg_version()
    url = f"https://api.github.com/repos/{repo}/releases/latest"
    try:
        with httpx.Client(timeout=5.0) as client:
            r = client.get(url, headers={"User-Agent": "ytx-update/1.0"})
            if r.status_code != 200:
                console.print(f"[yellow]Update check failed: status {r.status_code}[/]")
                return
            data = r.json()
            latest = data.get("tag_name") or data.get("name") or "unknown"
            if latest.lstrip('v') != current:
                console.print(f"[yellow]A new version may be available[/]: {latest} (local {current})")
            else:
                console.print(f"[green]You are up to date[/]: {current}")
    except Exception as e:
        console.print(f"[yellow]Update check error[/]: {e}")

if __name__ == "__main__":
    try:
        app()
    except KeyboardInterrupt:
        console.print("[yellow]Aborted by user[/]")
        raise SystemExit(130)
    except Exception as e:
        try:
            from .errors import friendly_error

            console.print(f"[red]{friendly_error(e)}[/]")
            raise SystemExit(1)
        except Exception:
            raise

# --- Export notes ---
@app.command("export")
def export_notes(
    video_id: str | None = typer.Option(None, "--video-id", help="Export from cache for this video id"),
    from_file: Path | None = typer.Option(None, "--from-file", exists=True, dir_okay=False, file_okay=True, readable=True, help="Export from a TranscriptDoc JSON file"),
    to: str = typer.Option("md", "--to", help="Export format (md only for now)"),
    output_dir: Path = typer.Option(..., "--output-dir", exists=True, file_okay=False, dir_okay=True, writable=True, help="Directory to write outputs"),
    md_frontmatter: bool = typer.Option(False, "--md-frontmatter/--no-md-frontmatter", help="Include YAML frontmatter in Markdown"),
    md_link_style: str = typer.Option("short", "--md-link-style", help="YouTube link style: short|long"),
    md_include_transcript: bool = typer.Option(False, "--md-include-transcript/--no-md-include-transcript", help="Append full transcript section"),
    md_include_chapters: bool = typer.Option(True, "--md-include-chapters/--no-md-include-chapters", help="Include chapter outline"),
    md_template: Path | None = typer.Option(None, "--md-template", exists=True, file_okay=True, dir_okay=False, readable=True, help="Optional template path for Markdown"),
    md_auto_chapters_min: float | None = typer.Option(None, "--md-auto-chapters-min", help="If no chapters found, synthesize chapters every N minutes"),
) -> None:
    """Export notes (Markdown) from cache or an input TranscriptDoc JSON file."""
    # Validate inputs
    if (video_id is None and from_file is None) or (video_id is not None and from_file is not None):
        raise typer.BadParameter("Provide exactly one of --video-id or --from-file")
    if to != "md":
        raise typer.BadParameter("Only --to md is supported in this version", param_hint=["--to"])
    if md_link_style not in {"short", "long"}:
        raise typer.BadParameter("--md-link-style must be short or long", param_hint=["--md-link-style"])

    # Load TranscriptDoc
    doc = None
    if from_file is not None:
        raw = from_file.read_text(encoding="utf-8")
        try:
            from .models import TranscriptDoc as _TD

            doc = _TD.model_validate_json(raw)
        except Exception:
            import json as _json

            payload = _json.loads(raw)
            from .models import TranscriptDoc as _TD

            doc = _TD.model_validate(payload)
    else:
        # Resolve latest cache entry for video_id and read transcript.json
        from .cache import scan_cache, TRANSCRIPT_JSON
        entries = [e for e in scan_cache() if e.video_id == video_id]
        if not entries:
            raise typer.BadParameter(f"No cache found for video id: {video_id}")
        # pick latest by created_at, fallback to lexicographic dir
        if len(entries) > 1:
            console.print(f"[yellow]Found {len(entries)} cache branches for {video_id}; selecting most recent[/]")
        entries.sort(key=lambda e: (e.created_at or __import__('datetime').datetime.min.replace(tzinfo=None), str(e.dir)))
        entry = entries[-1]
        json_path = entry.dir / TRANSCRIPT_JSON
        if not json_path.exists():
            # Fallback to <video_id>.json within the same dir
            alt = entry.dir / f"{entry.video_id}.json"
            if alt.exists():
                json_path = alt
            else:
                raise typer.BadParameter(f"Cached transcript not found at: {json_path} or {alt}")
        raw = json_path.read_text(encoding="utf-8")
        try:
            from .models import TranscriptDoc as _TD

            doc = _TD.model_validate_json(raw)
        except Exception:
            import json as _json

            payload = _json.loads(raw)
            from .models import TranscriptDoc as _TD

            doc = _TD.model_validate(payload)

    # Export via MarkdownExporter
    exp = MarkdownExporter(
        frontmatter=md_frontmatter,
        link_style=md_link_style,  # type: ignore[arg-type]
        include_transcript=md_include_transcript,
        include_chapters=md_include_chapters,
        template=md_template,
        auto_chapter_every_sec=(md_auto_chapters_min * 60.0) if (md_auto_chapters_min and md_auto_chapters_min > 0) else None,
    )
    path = exp.export(doc, output_dir)
    console.print(f"[green]Wrote[/]: {path}")
# Health checks
@app.command("health")
def health() -> None:
    """Run basic health checks: ffmpeg, API keys, and network."""
    from rich.table import Table
    from .audio import ensure_ffmpeg
    import os, shutil
    import httpx

    checks: list[tuple[str, str]] = []

    # FFmpeg
    try:
        ensure_ffmpeg()
        checks.append(("ffmpeg", "ok"))
    except Exception as e:
        checks.append(("ffmpeg", f"missing: {e}"))

    # Engines availability / configuration
    try:
        __import__("faster_whisper")
        checks.append(("whisper_engine", "available"))
    except Exception:
        checks.append(("whisper_engine", "unavailable"))

    env_bin = os.environ.get("YTX_WHISPERCPP_BIN")
    cpp_found = (shutil.which(env_bin) if env_bin else None) or shutil.which("main")
    checks.append(("whispercpp_bin", "configured" if env_bin and (cpp_found or os.path.isfile(env_bin)) else ("present" if cpp_found else "absent")))

    # API keys
    key_g = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    checks.append(("gemini_api_key", "present" if key_g else "absent"))

    key_o = os.environ.get("OPENAI_API_KEY")
    if key_o:
        checks.append(("openai_api_key", "present" if (key_o.startswith("sk-") and len(key_o) > 20) else "invalid"))
    else:
        checks.append(("openai_api_key", "absent"))

    key_d = os.environ.get("DEEPGRAM_API_KEY")
    checks.append(("deepgram_api_key", "present" if key_d else "absent"))

    # Tools
    ytdlp = shutil.which("yt-dlp")
    checks.append(("yt_dlp", "ok" if ytdlp else "missing"))

    # Network
    try:
        with httpx.Client(timeout=5.0, follow_redirects=True) as client:
            r = client.get("https://www.google.com", headers={"User-Agent": "ytx-health/1.0"})
            ok = r.status_code < 500
        checks.append(("network", "ok" if ok else f"status {r.status_code}"))
    except Exception as e:
        checks.append(("network", f"error: {e}"))

    table = Table(title="ytx health")
    table.add_column("Check")
    table.add_column("Status")

    def _color(v: str) -> str:
        if any(x in v for x in ("ok", "present", "available", "configured", "status 2")):
            return "green"
        if any(x in v for x in ("invalid", "absent")):
            return "yellow"
        if any(x in v for x in ("missing", "unavailable", "error")):
            return "red"
        return "white"

    for k, v in checks:
        table.add_row(k, f"[{_color(v)}]{v}[/]")
    console.print(table)
