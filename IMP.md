# Implementation Plan (IMP)

Lean, pragmatic plan to build a CLI and minimal Python API that takes a YouTube URL, downloads audio, and returns transcripts and captions using either local Whisper (faster‑whisper) or Gemini Flash. Managed with `uv` for reproducible Python builds.

## 1) Objectives & Scope
- Primary: `ytx transcribe <youtube_url>` outputs transcript JSON and SRT (VTT, TXT as future enhancements).
- Engines: Local Whisper (via faster‑whisper) and Gemini Flash (via Google Generative AI API).
- Extras (optional flags): chapter-aware processing, summary generation, caching.
- Non-goals: full web UI, speaker diarization, live stream transcription.

## 2) High-level Architecture
- CLI (Typer) orchestrates a pipeline:
  1) Resolve URL → metadata (id, title, duration, chapters) via yt-dlp.
  2) Download best audio stream to cache.
  3) Normalize audio to 16 kHz mono WAV via ffmpeg.
  4) Transcribe via selected engine (Whisper or Gemini).
  5) Post-process segments (merge/split, punctuation if needed).
  6) Export artifacts (JSON, SRT) into a content-addressed cache.
  7) Optional: summarize and chapterize.
- Caching keyed by `(video_id, engine, model, config_hash)` to make runs idempotent.
- Logging (rich) with structured events and progress bars.

## 3) Repo & Package Layout
```
.
├─ ytx/
│  ├─ __init__.py
│  ├─ cli.py                   # Typer app entry
│  ├─ config.py                # Config model + config hash
│  ├─ logging.py               # Rich console + structured logs
│  ├─ models.py                # Pydantic models (Transcript, Segment, Chapter)
│  ├─ downloader.py            # yt-dlp metadata + audio download
│  ├─ audio.py                 # ffmpeg normalize, slicing, utils
│  ├─ cache.py                 # cache paths, artifact existence, reads/writes
│  ├─ chapters.py              # chapter-aware slicing + stitching
│  ├─ exporters/
│  │  ├─ json_exporter.py
│  │  └─ srt_exporter.py
│  └─ engines/
│     ├─ base.py               # Engine interface
│     ├─ whisper_engine.py     # faster-whisper implementation
│     └─ gemini_engine.py      # Gemini Flash implementation
├─ tests/                      # unit + light e2e (no secrets)
├─ scripts/                    # helper scripts (optional)
├─ data/                       # (gitignored) raw/wav during dev if desired
├─ artifacts/                  # (gitignored) output cache during dev
├─ IMP.md                      # this document
├─ PRD.md                      # high-level PRD (optional)
├─ README.md                   # quickstart & examples
├─ .env.example                # env var hints (GEMINI_API_KEY, GEMINI_MODEL)
└─ pyproject.toml              # managed by uv
```

Notes:
- Default cache should live under XDG cache: `~/.cache/ytx/…`. Keep `artifacts/` working-dir override for convenience.
- `tests/` include small audio samples and integration against public short videos.

## 4) Tooling & Dependencies
- Python: 3.11+
- System: ffmpeg installed and discoverable (`ffmpeg -version`).
- Python packages:
  - Core: `typer[all]`, `rich`, `pydantic>=2`, `orjson`, `tenacity`, `httpx`, `srt`, `python-dotenv`.
  - Download/Audio: `yt-dlp`, optional `pydub` (utility), but prefer raw ffmpeg.
  - Local STT: `faster-whisper` (CTranslate2 backend). Optional: `numba` if needed.
  - Cloud STT: `google-generativeai` (Gemini). Alternative (optional): Google STT v2.
- Manage via `uv`:
  - `uv init --package ytx`
  - `uv add typer[all] rich pydantic orjson tenacity httpx yt-dlp srt python-dotenv faster-whisper google-generativeai`

## 5) Configuration & Secrets
- Environment-first; CLI flags override.
- Env vars:
  - `GEMINI_API_KEY` (required for Gemini engine).
  - `GEMINI_MODEL` (default: `gemini-2.5-flash`).
  - `WHISPER_MODEL` (default: `large-v3-turbo`).
  - `WHISPER_COMPUTE_TYPE` (default: `int8` for Apple Silicon/CPU, `auto` for GPU).
  - `YTX_CACHE_DIR` (default XDG `~/.cache/ytx`).
  - `YTX_OUTPUT_DIR` (optional override per run; also via `--output-dir`).
- `.env` loading with `python-dotenv`.
- Never log secrets.

## 6) CLI UX
- Entry: `ytx` (installed via `pyproject` scripts)
- Commands:
  - `ytx transcribe <url_or_path>`
    - Flags: `--engine [whisper|gemini]`, `--model <name>`, `--language <code|auto>`, `--chapters/--no-chapters`, `--summarize/--no-summarize`, `--output-dir`, `--overwrite`, `--format srt,json`, `--device cpu|auto`, `--compute-type int8|auto`, `--verbose`.
  - `ytx cache ls|clear`
  - `ytx audio <url> --out <path>` (debug helper)

Examples:
- `uv run ytx transcribe https://youtu.be/abc --engine whisper --model large-v3-turbo`
- `uv run ytx transcribe https://youtu.be/abc --engine gemini --summarize`

## 7) Data Model
Pydantic models for safety and export:
- `TranscriptDoc`:
  - meta: `video_id`, `source_url`, `title`, `duration`, `language`, `engine`, `engine_version?`, `model`, `created_at`, `config_hash`.
  - `segments: list[TranscriptSegment]`.
  - `chapters?: list[Chapter]`.
  - `summary?: Summary`.
- `TranscriptSegment`: `{id:int, start:float, end:float, text:str, confidence:float|None}`
- `Chapter`: `{title:str|None, start:float, end:float, summary:str|None}`
- `Summary`: `{tldr:str, bullets:list[str]}`

JSON export uses `orjson` with stable key ordering.

## 8) Detailed Pipeline
1) Resolve + metadata (yt-dlp)
   - `yt-dlp --dump-json --no-download <url>` → parse `id`, `title`, `duration`, `chapters?`, `uploader`, etc.
   - Validate: not live, not age/region restricted. If restricted, allow `--cookies-from-browser` and/or cookie file path.
2) Download audio
   - `yt-dlp -f bestaudio --extract-audio --audio-format m4a --audio-quality 0 -o '<id>.%(ext)s'` to cache dir.
   - Use explicit `bestaudio` selector for optimal audio-only download.
   - Retry with backoff; resumable downloads.
   - Support for cookies/auth: `--cookies-from-browser` or `--cookies <file>` for restricted content.
3) Normalize WAV
   - `ffmpeg -i <in> -vn -ac 1 -ar 16000 -c:a pcm_s16le <id>.wav` (idempotent; skip if exists unless `--overwrite`).
4) Chapter-aware slicing (optional)
   - If chapters present and `--chapters`, slice WAV per chapter (±2s overlap). Process in parallel where safe.
   - Else use full audio. Optional VAD-based chunking for very long audio.
5) Engine: Whisper (local)
   - Load model: `faster-whisper` with user model (default `large-v3-turbo` for best speed/accuracy, fallback to `large-v3` for streaming), quantization `int8` for Apple Silicon.
   - `transcribe()` with params: `batch_size=8` (batched inference for 2-4x speed), `beam_size=5` (size-dependent), `vad_filter=True`, `language=auto|code`, `word_timestamps=True` when feasible, `compute_type="int8"` on CPU/Apple Silicon.
   - Convert generator output to `TranscriptSegment`; compute confidences when available.
6) Engine: Gemini (cloud)
   - Auth via `GEMINI_API_KEY`. Select model via `GEMINI_MODEL` (e.g., `gemini-2.5-flash`), configurable.
   - For short audio (within file API limits): upload audio file and request transcription. For long audio: chunk into 5–10 min windows with ~2s overlaps; send sequential or limited parallel requests.
   - Prompting strategy: ask for verbatim transcript with timestamps; request JSON lines with fields `{start, end, text}`; include `chunk_start_offset` in the prompt; post-adjust times on merge.
   - Stitching: time-shift by chunk offset; merge overlapping segments; dedupe near-duplicate text across overlaps.
   - Note: exact timestamp fidelity from a general LLM may vary; prefer Whisper for precise timestamps. Optionally use Gemini to clean/punctuate Whisper text and to summarize.
7) Post-processing
   - Normalize whitespace, fix capitalization if desired, merge tiny segments, enforce max line length for captions.
   - Language detection: from engine or light heuristic if not provided.
8) Exporters
   - JSON: full document with segments.
   - SRT: convert segments; 32–80 chars per caption; max 2 lines; split on punctuation or whitespace boundaries; ensure increasing times.
9) Caching & Idempotency
   - Compute `config_hash = sha256(sorted_json(config_subset))` including engine, model, language, chunking, chapters flag, summarization, and exporter options.
   - Artifacts path: `<cache_root>/<video_id>/<engine>/<model>/<config_hash>/` containing `meta.json`, `transcript.json`, `captions.srt`.

## 9) Concurrency & Performance
- Use `concurrent.futures.ThreadPoolExecutor` for blocking IO (yt-dlp, ffmpeg invocations) and CPU-light stitching.
- Limit parallel transcoding for Whisper to avoid memory spikes; per-chapter parallelism if model fits.
- For Gemini, bound concurrency (e.g., 2–3 in flight) and use `tenacity` retry with jitter.
- Apple Silicon: use `device='cpu'` with `compute_type='int8'` by default for optimal performance. Allow user override `--device` and `--compute-type` if GPU available.

## 10) Error Handling & Resilience
- Wrap external calls with retries and clear user-facing errors.
- Detect and short-circuit for live/ongoing streams.
- If Gemini quota/rate limit, backoff and resume; surface partial progress.
- For low SNR or music-only content, emit low-confidence notice.
- Validate all outputs and fail fast if exporters would emit empty files.

## 11) Logging & Observability
- Rich console with progress bars per stage (download, normalize, transcribe, export).
- Structured log events for timings and cache hits.
- `--verbose` toggles debug details; default is info-level.

## 12) Testing Strategy
- Unit tests:
  - downloader metadata parsing
  - ffmpeg normalization command builder
  - chunking and stitching logic
  - exporters produce valid SRT/VTT
  - config hash stability
- Integration (no secrets):
  - Public short YT video end-to-end using Whisper tiny model
  - Golden outputs (hash-insensitive) for SRT/VTT formatting
- Cloud path:
  - Run only when `GEMINI_API_KEY` present; otherwise mocked responses.
- E2E script: transcribe known 15–30s clip; assert artifacts exist and schema validates.

## 13) Milestones & Acceptance Criteria
- M1: Scaffold + Download/Export pipeline
  - Repo scaffold with `uv`, Typer CLI, logging.
  - yt-dlp metadata + audio download; ffmpeg normalization.
  - JSON/SRT exporters with basic segmentation.
  - AC: `ytx transcribe <url> --engine whisper --model tiny` runs to completion using a mocked/dummy transcript until M2.
- M2: Whisper engine
  - Implement faster‑whisper path with language auto-detect and timestamps.
  - Caching, config hash, and idempotency.
  - AC: End-to-end transcript on ≥60s video ≤6× realtime on M-series with small model; artifacts cached.
- M3: Gemini engine + summaries
  - Implement Gemini upload/chunking and timestamped JSON output; merge logic.
  - Optional `--summarize` using Gemini over final transcript.
  - AC: End-to-end transcript on ≤30 min video by chunking; summary included when requested.
- M4: Chapters-aware mode
  - Per-chapter processing, stitching, and optional per-chapter summaries.
  - AC: For videos with chapters, outputs include chapter list aligned with transcript.
- M5: Polish & tests
  - Robust CLI UX, error messages, retries; test coverage for core utilities.
  - AC: `make test` or `uv run pytest` passes; docs updated.

## 14) Work Backlog (Detailed Tasks)
- Project setup
  - Initialize with `uv init`, configure `pyproject.toml`, add console script `ytx=ytx.cli:app`.
  - Add `README.md`, `.env.example`, `PRD.md` link to IMP.
- CLI & Config
  - Implement Typer app and global options; load env; compute config hash.
  - Implement `cache ls|clear` and `audio` helpers.
- Downloader & Audio
  - yt-dlp metadata fetch + parse; bestaudio download with retries.
  - ffmpeg normalize to WAV 16 kHz mono; duration probe.
- Models & Cache
  - Pydantic models; `cache.py` for layout; atomic writes for artifacts.
- Exporters
  - JSON exporter with orjson
  - SRT exporter; caption segmentation utility
- Whisper Engine
  - Wrapper over faster‑whisper; model load cache; params selection; generator to segments.
- Gemini Engine
  - Client setup with `google-generativeai`
  - File upload + generate content; prompt template for timestamped JSON
  - Chunking strategy and stitching utilities
  - Rate limit/resilience with tenacity
- Chapters Mode
  - Slice audio per chapter; run engine per slice; merge; optional per-chapter summaries
- Summarization
  - Prompt over final transcript to generate TL;DR + bullets; optional per-chapter one-liners
- Testing & CI (local)
  - Unit tests for utilities; fixture for small sample video
  - Mock Gemini for offline runs

## 15) Pseudocode Sketches
Transcribe command:
```python
@app.command()
def transcribe(
    target: str, 
    engine: str = "whisper", 
    model: str = None,  # Will use env var defaults
    language: str|None = None, 
    chapters: bool = False, 
    summarize: bool = False, 
    output_dir: Path|None = None, 
    overwrite: bool = False, 
    format: str = "json,srt", 
    device: str = "cpu",
    compute_type: str = None  # Will default to int8 for CPU/Apple Silicon
):
    # Load defaults from env
    if model is None:
        model = os.getenv("WHISPER_MODEL", "large-v3-turbo") if engine == "whisper" else os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    if compute_type is None:
        compute_type = os.getenv("WHISPER_COMPUTE_TYPE", "int8" if device == "cpu" else "auto")
    
    cfg = build_config(engine=engine, model=model, language=language, chapters=chapters, summarize=summarize, device=device, compute_type=compute_type)
    meta = fetch_metadata(target)
    cache_dir = compute_cache_dir(meta.video_id, cfg)
    if not overwrite and artifacts_exist(cache_dir):
        return load_artifacts(cache_dir)

    audio_path = download_audio(meta, cache_dir)
    wav_path = normalize_wav(audio_path, cache_dir)

    if chapters and meta.chapters:
        segments = []
        for ch in meta.chapters:
            wav_seg = slice_audio(wav_path, ch.start, ch.end, overlap=2.0)
            segs = transcribe_engine(engine, wav_seg, cfg, offset=ch.start)
            segments.extend(segs)
        segments = stitch_segments(segments)
    else:
        segments = transcribe_engine(engine, wav_path, cfg, offset=0.0)

    doc = TranscriptDoc.from_segments(meta=meta, segments=segments, config_hash=cfg.hash)

    if summarize:
        doc.summary = summarize_doc(doc, engine="gemini")  # Use Gemini for summaries

    export_all(doc, output_dir or cache_dir, formats=parse_formats(format))
```

Gemini engine (chunking):
```python
def transcribe_gemini(wav_path: Path, cfg: Config, offset: float = 0.0) -> list[TranscriptSegment]:
    if audio_duration(wav_path) <= cfg.gemini.max_minutes:
        parts = [make_gemini_part(wav_path)]
        msgs = build_transcription_prompt(offset=offset)
        chunks = [gemini_call(parts, msgs)]
    else:
        windows = sliding_windows(wav_path, minutes=cfg.gemini.window, overlap=cfg.gemini.overlap)
        chunks = []
        for win in windows:
            parts = [make_gemini_part(win.path)]
            msgs = build_transcription_prompt(offset=offset + win.start)
            chunks.append(gemini_call(parts, msgs))
    segs = [parse_segment_json(x) for x in chunks]
    return stitch_segments(flatten(segs))
```

Whisper engine:
```python
def transcribe_whisper(wav_path: Path, cfg: Config, offset: float = 0.0) -> list[TranscriptSegment]:
    model = load_faster_whisper(
        cfg.model or "large-v3-turbo",  # Default to turbo model
        device=cfg.device,
        compute_type=cfg.compute_type or "int8"  # Default to int8
    )
    res, _ = model.transcribe(
        str(wav_path), 
        vad_filter=True, 
        language=cfg.language, 
        beam_size=cfg.beam_size,
        word_timestamps=cfg.word_ts,
        batch_size=8  # Enable batched inference
    )
    segs = []
    for i, s in enumerate(res):
        segs.append(TranscriptSegment(id=i, start=s.start+offset, end=s.end+offset, text=s.text.strip(), confidence=getattr(s, 'avg_logprob', None)))
    return segs
```

## 16) Implementation Notes & Decisions
- Prefer Whisper for precise timestamps. Use Gemini for summaries or when local compute unavailable; when using Gemini for transcription, expose a disclaimer about approximate timestamps and provide a “cleanup via LLM” option for Whisper output.
- Chapter-aware mode is a big accuracy win; encourage via CLI help when chapters present.
- Cache robustness: write artifacts atomically to temp then move; include `meta.json` for provenance.
- Time formats: seconds (float) internally; convert to SRT HH:MM:SS,mmm and VTT HH:MM:SS.mmm at export.
- Large videos: For Whisper, VAD and chunked decode keep memory bounded; for Gemini, chunk by time windows with overlaps.

## 17) Risks & Mitigations
- Gemini timestamp fidelity: Mitigate by recommending Whisper for timestamps, or hybrid: Whisper timestamps + Gemini cleanup.
- Rate limits / quotas: Implement exponential backoff and partial progress; expose `--max-concurrency`.
- ffmpeg/yt-dlp availability: Provide clear install instructions; preflight check and actionable error if missing.
- Long-duration processing time: Surface ETA via progress; allow resume from cache.
- Changes in Google API/model names: Make `GEMINI_MODEL` configurable; document how to update.

## 18) Future Enhancements
- Thin HTTP service with queue for batch jobs.
- Word-level timestamps and karaoke-style captions.
- Speaker diarization (pyannote) as future enhancement.
- Alternative STT backends (Vosk, WhisperX, Cloud STT v2) behind the same interface.

## 19) Setup Snippets (reference)
- Initialize project
  - `uv init --package ytx`
  - `uv add typer[all] rich pydantic orjson tenacity httpx yt-dlp srt python-dotenv faster-whisper google-generativeai`
- Dev run
  - `uv run ytx transcribe https://youtu.be/<id> --engine whisper --model small`
- With Gemini
  - `export GEMINI_API_KEY=...`
  - `uv run ytx transcribe https://youtu.be/<id> --engine gemini --summarize`

## 20) Acceptance Checklist (Go/No‑Go)
- `ytx transcribe <url>` produces valid `.json`, `.srt`.
- Cache hit on repeat runs without `--overwrite`.
- Whisper path works offline (network disabled) beyond yt-dlp.
- Gemini path works with `GEMINI_API_KEY` and offers chunking for long audios.
- Logs are informative; errors actionable.
- Basic tests pass locally via `uv run pytest`.

---
This plan keeps scope tight while leaving room to evolve. Next step: scaffold the repo with `uv`, create the CLI entry, and stub both engines to enable an end‑to‑end “hello transcript” on a short video.
