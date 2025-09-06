# Phase 1: Foundation & Core Pipeline

## Overview
Phase 1 establishes the foundation for the YouTube transcription tool with basic functionality. Focus on core infrastructure, simple Whisper transcription, and essential features.

**Duration**: ~60 tickets × 3 hours average = 180 hours (~4.5 weeks at full-time)
**Goal**: Achieve basic end-to-end transcription with local Whisper engine

---

## Sprint 1: Project Setup & Infrastructure (8 tickets)

### SETUP-001: Initialize UV Project
**Acceptance Criteria:**
- Run `uv init --package ytx` successfully
- Project structure created with src/ytx folder
- pyproject.toml generated with basic metadata
**Technical Notes:** Use Python 3.11+
**Dependencies:** None
**Time:** 2 hours

Status: Completed
Verification:
- Created `ytx/` project with src layout at `ytx/src/ytx/__init__.py`.
- Generated `ytx/pyproject.toml` with a `[project]` table.

### SETUP-002: Configure pyproject.toml Metadata
**Acceptance Criteria:**
- Add project description, author, version (0.1.0)
- Set Python requirement to >=3.11
- Add homepage and repository URLs
**Technical Notes:** Follow PEP 621 standards
**Dependencies:** SETUP-001
**Time:** 2 hours

Status: Completed
Verification:
- Updated `ytx/pyproject.toml`: `version = "0.1.0"`, description set, author added.
- `requires-python = ">=3.11"` configured.
- Added `[project.urls]` with Homepage, Repository, and Issues.

### SETUP-003: Create Basic Project Structure
**Acceptance Criteria:**
- Create folders: ytx/, tests/, scripts/, data/, artifacts/
- Add __init__.py files where needed
- Create .gitignore with proper Python patterns
**Technical Notes:** Include artifacts/ and data/ in .gitignore
**Dependencies:** SETUP-001
**Time:** 2 hours

Status: Completed
Verification:
- Created directories under `ytx/`: `tests/`, `scripts/`, `data/`, `artifacts/`.
- Added `ytx/tests/__init__.py`.
- Updated `ytx/.gitignore` to include `data/` and `artifacts/` (plus `.env`).

### SETUP-004: Add Core Dependencies
**Acceptance Criteria:**
- Run `uv add typer[all] rich pydantic orjson`
- Dependencies added to pyproject.toml
- uv.lock file created
**Technical Notes:** Use exact versions for reproducibility
**Dependencies:** SETUP-001
**Time:** 2 hours

Status: Completed
Verification:
- Ran `uv add typer[all] rich pydantic orjson` inside `ytx/`.
- `ytx/pyproject.toml` now lists: `typer`, `rich`, `pydantic`, `orjson` under `[project.dependencies]`.
- uv operates in a workspace; lock generated at workspace root: `/Users/prateek/uv.lock` (present).

Notes
- Typer 0.15 no longer exposes the `all` extra; dependency updated to `typer>=0.15.2` (no extras). Reproducibility is ensured via `uv.lock`.

### SETUP-005: Add Processing Dependencies
**Acceptance Criteria:**
- Run `uv add tenacity httpx srt python-dotenv`
- Verify all packages install without conflicts
**Technical Notes:** Check compatibility with Python 3.11
**Dependencies:** SETUP-004
**Time:** 2 hours

Status: Completed
Verification:
- Ran `uv add tenacity httpx srt python-dotenv` in `ytx/`.
- `ytx/pyproject.toml` lists: `tenacity`, `httpx`, `srt`, `python-dotenv`.
- Workspace lockfile updated at `/Users/prateek/uv.lock` (timestamp refreshed).
Notes:
- All selected versions are compatible with Python 3.11.

### SETUP-006: Add Media Dependencies
**Acceptance Criteria:**
- Run `uv add yt-dlp faster-whisper`
- Verify ffmpeg is available on system
- Add ffmpeg check to README
**Technical Notes:** Document ffmpeg installation for each OS
**Dependencies:** SETUP-004
**Time:** 3 hours

Status: Completed
Verification:
- Installed media deps: `uv add yt-dlp faster-whisper` inside `ytx/` (workspace lock updated).
- FFmpeg availability: present — `ffmpeg version 8.0` (Apple clang build).
- Updated `ytx/README.md` with FFmpeg check and install instructions (macOS, Linux, Windows).

### SETUP-007: Create .env.example
**Acceptance Criteria:**
- Create .env.example with all env variables
- Add comments explaining each variable
- Include WHISPER_MODEL=large-v3-turbo
**Technical Notes:** Do not commit actual .env file
**Dependencies:** SETUP-003
**Time:** 2 hours

Status: Completed
Verification:
- Added `ytx/.env.example` with documented variables: `YTX_ENGINE`, `WHISPER_MODEL=large-v3-turbo`, `WHISPER_DEVICE`, `WHISPER_COMPUTE_TYPE`, `GEMINI_API_KEY`, `GEMINI_MODEL`, `YTX_CACHE_DIR`, `YTX_OUTPUT_DIR`, `YTX_MAX_CONCURRENCY`, `YTX_HTTP_TIMEOUT`, and yt‑dlp cookie options.
- `.env` is ignored via `ytx/.gitignore`.

### SETUP-008: Setup Entry Point
**Acceptance Criteria:**
- Add console script in pyproject.toml: ytx=ytx.cli:app
- Verify `uv run ytx --help` works
- Create empty cli.py with placeholder
**Technical Notes:** Use [project.scripts] section
**Dependencies:** SETUP-004
**Time:** 2 hours

Status: Completed
Verification:
- Updated `ytx/pyproject.toml` `[project.scripts]` to `ytx = "ytx.cli:app"`.
- Added `ytx/src/ytx/cli.py` with a minimal Typer app (commands: `version-cmd`, `hello`).
- `cd ytx && uv run ytx --help` shows usage and commands successfully.

---

## Sprint 2: Core Models & Configuration (10 tickets)

### MODEL-001: Create Base Pydantic Models
**Acceptance Criteria:**
- Create models.py with BaseModel imports
- Add model_config with ConfigDict
- Set up proper validation settings
**Technical Notes:** Use Pydantic v2 patterns
**Dependencies:** SETUP-004
**Time:** 2 hours

Status: Completed
Verification:
- Added `ytx/src/ytx/models.py` with a strict `ModelBase` (Pydantic v2 `ConfigDict`).
- Included orjson-backed JSON serialization and common type aliases: `Seconds`, `NonEmptyStr`.

### MODEL-002: Define TranscriptSegment Model
**Acceptance Criteria:**
- Create TranscriptSegment with id, start, end, text, confidence
- Add field validators for time ranges
- Ensure start < end validation
**Technical Notes:** Times as float (seconds)
**Dependencies:** MODEL-001
**Time:** 3 hours

Status: Completed
Verification:
- Implemented `TranscriptSegment` in `ytx/src/ytx/models.py` with fields: `id`, `start`, `end`, `text`, `confidence`.
- Uses shared `Seconds` and `NonEmptyStr` types; validator enforces `end > start`.

### MODEL-003: Define Chapter Model
**Acceptance Criteria:**
- Create Chapter model with title, start, end, summary
- Add optional fields handling
- Validate time ranges
**Technical Notes:** Summary is optional
**Dependencies:** MODEL-001
**Time:** 2 hours

Status: Completed
Verification:
- Implemented `Chapter` in `ytx/src/ytx/models.py` with fields: `title` (optional), `start`, `end`, `summary` (optional).
- Validator enforces `end > start`; added `duration` convenience property.

### MODEL-004: Define Summary Model
**Acceptance Criteria:**
- Create Summary with tldr and bullets fields
- Bullets as list[str]
- Add string length validators
**Technical Notes:** Max 500 chars for tldr
**Dependencies:** MODEL-001
**Time:** 2 hours

Status: Completed
Verification:
- Added `Summary` to `ytx/src/ytx/models.py` with `tldr` (max_length=500) and `bullets: list[str]` using `NonEmptyStr`.

### MODEL-005: Define TranscriptDoc Model
**Acceptance Criteria:**
- Create main document model with metadata
- Include segments list, optional chapters and summary
- Add creation timestamp
**Technical Notes:** Use datetime.utcnow()
**Dependencies:** MODEL-002, MODEL-003, MODEL-004
**Time:** 3 hours

Status: Completed
Verification:
- Implemented `TranscriptDoc` in `ytx/src/ytx/models.py` with metadata fields (`video_id`, `source_url`, `title`, `duration`, `language`, `engine`, `model`), `created_at` defaulting to `datetime.utcnow()`, and content (`segments`, optional `chapters`, optional `summary`).

### MODEL-006: Create Config Model
**Acceptance Criteria:**
- Create config.py with Config class
- Include engine, model, language fields
- Add device and compute_type settings
**Technical Notes:** Use Pydantic BaseSettings
**Dependencies:** MODEL-001
**Time:** 3 hours

Status: Completed
Verification:
- Added `ytx/src/ytx/config.py` with `AppConfig` (`engine`, `model`, `language`, `device`, `compute_type`) based on Pydantic `BaseSettings`.
- Defaults set (engine=whisper, model=small, device=cpu, compute_type=int8); env prefix `YTX_` reserved for later expansion.

### MODEL-007: Implement Config Hash
**Acceptance Criteria:**
- Add method to compute config hash
- Use SHA256 of sorted JSON
- Include relevant fields only
**Technical Notes:** Use orjson for deterministic output
**Dependencies:** MODEL-006
**Time:** 3 hours

Status: Completed
Verification:
- Added `config_hash()` and `_hash_input()` to `ytx/src/ytx/config.py` using SHA256 of sorted JSON (orjson fallback to stdlib).
- `_hash_input` includes: engine, model, language (if set), device, compute_type.
- Runtime check via `uv run` prints deterministic hash for defaults.

### MODEL-008: Add Environment Loading
**Acceptance Criteria:**
- Load .env file with python-dotenv
- Override with environment variables
- Set proper defaults
**Technical Notes:** Use load_dotenv(override=False)
**Dependencies:** MODEL-006
**Time:** 2 hours

Status: Completed
Verification:
- Added `load_config()` in `ytx/src/ytx/config.py` which calls `load_dotenv(override=False)` then builds `AppConfig`.
- `AppConfig` also honors `.env` via `SettingsConfigDict(env_file=(".env",))`; env vars override file values.

### MODEL-009: Create Video Metadata Model
**Acceptance Criteria:**
- Add VideoMetadata with id, title, duration, url
- Include optional uploader, description
- Parse duration to seconds
**Technical Notes:** Handle various duration formats
**Dependencies:** MODEL-001
**Time:** 3 hours

Status: Completed
Verification:
- Implemented `VideoMetadata` in `ytx/src/ytx/models.py` with coercion for `duration`:
  - Supports floats/ints, `HH:MM:SS`/`MM:SS`, and ISO8601 like `PT1H2M3S`.
- Quick `uv run` sanity validated parsing to seconds.

### MODEL-010: Add Model Serialization Methods
**Acceptance Criteria:**
- Add .model_dump_json() usage examples
- Configure orjson serialization
- Ensure stable key ordering
**Technical Notes:** Use sort_keys=True
**Dependencies:** MODEL-005
**Time:** 2 hours

Status: Completed
Verification:
- `ModelBase` uses orjson for JSON serialization; updated to sort keys (`OPT_SORT_KEYS`) for deterministic output.
- All models inherit `ModelBase`, so `.model_dump_json()` yields stable ordering.

---

## Sprint 3: Downloader & Audio Processing (12 tickets)

### DOWNLOAD-001: Create downloader.py Module
**Acceptance Criteria:**
- Create downloader.py file
- Add basic imports and structure
- Set up logging with rich
**Technical Notes:** Use rich.logging.RichHandler
**Dependencies:** SETUP-003
**Time:** 2 hours

Status: Completed
Verification:
- Added `ytx/src/ytx/downloader.py` with module skeleton and Rich logging (`RichHandler`).
- Included `is_youtube_url()` helper and placeholders (`fetch_metadata`) for next ticket.

### DOWNLOAD-002: Implement Metadata Fetcher
**Acceptance Criteria:**
- Function to run yt-dlp --dump-json
- Parse JSON response
- Return VideoMetadata object
**Technical Notes:** Use subprocess.run with timeout
**Dependencies:** MODEL-009, DOWNLOAD-001
**Time:** 4 hours

Status: Completed
Verification:
- Implemented `fetch_metadata(url, timeout=90, cookies_from_browser=None, cookies_file=None)` in `ytx/src/ytx/downloader.py`.
- Uses `subprocess.run` with `--no-playlist --dump-json --no-download`; parses JSON and returns `VideoMetadata`.
- Error handling for missing yt-dlp, timeout, non-zero exit, and malformed JSON; logs an info line on success.

### DOWNLOAD-003: Add URL Validation
**Acceptance Criteria:**
- Validate YouTube URL format
- Support youtu.be and youtube.com
- Extract video ID from URL
**Technical Notes:** Use regex patterns
**Dependencies:** DOWNLOAD-001
**Time:** 3 hours

### DOWNLOAD-004: Implement Audio Download
**Acceptance Criteria:**
- Download with yt-dlp -f bestaudio
- Save to specified directory
- Return path to downloaded file
**Technical Notes:** Use --audio-quality 0
**Dependencies:** DOWNLOAD-002
**Time:** 4 hours

### DOWNLOAD-005: Add Download Progress Bar
**Acceptance Criteria:**
- Show rich progress bar during download
- Parse yt-dlp progress output
- Update bar in real-time
**Technical Notes:** Use rich.progress.Progress
**Dependencies:** DOWNLOAD-004
**Time:** 3 hours

### DOWNLOAD-006: Create audio.py Module
**Acceptance Criteria:**
- Create audio.py file
- Add ffmpeg wrapper functions
- Set up error handling
**Technical Notes:** Check ffmpeg availability
**Dependencies:** SETUP-003
**Time:** 2 hours

### DOWNLOAD-007: Implement WAV Normalization
**Acceptance Criteria:**
- Convert to 16kHz mono WAV
- Use ffmpeg command construction
- Handle various input formats
**Technical Notes:** -ar 16000 -ac 1 -c:a pcm_s16le
**Dependencies:** DOWNLOAD-006
**Time:** 3 hours

### DOWNLOAD-008: Add Audio Duration Check
**Acceptance Criteria:**
- Get duration using ffprobe
- Parse output correctly
- Return duration in seconds
**Technical Notes:** Use ffprobe -show_entries
**Dependencies:** DOWNLOAD-006
**Time:** 3 hours

### DOWNLOAD-009: Implement File Caching Check
**Acceptance Criteria:**
- Check if audio already downloaded
- Verify file integrity (size > 0)
- Skip if exists unless overwrite
**Technical Notes:** Use Path.exists() and stat()
**Dependencies:** DOWNLOAD-004
**Time:** 2 hours

### DOWNLOAD-010: Add Retry Logic
**Acceptance Criteria:**
- Wrap download in tenacity retry
- Exponential backoff on failure
- Max 3 retry attempts
**Technical Notes:** Use @retry decorator
**Dependencies:** DOWNLOAD-004
**Time:** 3 hours

### DOWNLOAD-011: Handle Restricted Content
**Acceptance Criteria:**
- Detect age/region restrictions
- Provide clear error message
- Suggest --cookies-from-browser option
**Technical Notes:** Parse yt-dlp error messages
**Dependencies:** DOWNLOAD-002
**Time:** 3 hours

### DOWNLOAD-012: Add Cookie Support
**Acceptance Criteria:**
- Accept cookies file path
- Pass to yt-dlp commands
- Document cookie extraction
**Technical Notes:** Use --cookies parameter
**Dependencies:** DOWNLOAD-004
**Time:** 3 hours

---

## Sprint 4: Basic Exporters (8 tickets)

### EXPORT-001: Create Exporters Package
**Acceptance Criteria:**
- Create exporters/ folder
- Add __init__.py with base class
- Define exporter interface
**Technical Notes:** Use ABC for interface
**Dependencies:** SETUP-003
**Time:** 2 hours

### EXPORT-002: Create Base Exporter Class
**Acceptance Criteria:**
- Abstract base class with export() method
- Common utility methods
- Path handling logic
**Technical Notes:** Use abc.ABC
**Dependencies:** EXPORT-001
**Time:** 3 hours

### EXPORT-003: Implement JSON Exporter
**Acceptance Criteria:**
- Create json_exporter.py
- Export TranscriptDoc to JSON
- Use orjson with sorted keys
**Technical Notes:** Ensure UTF-8 encoding
**Dependencies:** EXPORT-002, MODEL-005
**Time:** 3 hours

### EXPORT-004: Add JSON Pretty Printing
**Acceptance Criteria:**
- Add indent option for readability
- Maintain stable key order
- Handle datetime serialization
**Technical Notes:** Use default handler for dates
**Dependencies:** EXPORT-003
**Time:** 2 hours

### EXPORT-005: Implement SRT Exporter
**Acceptance Criteria:**
- Create srt_exporter.py
- Convert segments to SRT format
- Handle time formatting correctly
**Technical Notes:** HH:MM:SS,mmm format
**Dependencies:** EXPORT-002
**Time:** 4 hours

### EXPORT-006: Add SRT Line Breaking
**Acceptance Criteria:**
- Split long lines (32-80 chars)
- Max 2 lines per caption
- Break on punctuation/spaces
**Technical Notes:** Preserve word boundaries
**Dependencies:** EXPORT-005
**Time:** 3 hours

### EXPORT-007: Implement Caption Numbering
**Acceptance Criteria:**
- Sequential numbering from 1
- Ensure no gaps in numbers
- Handle empty segments
**Technical Notes:** Filter empty text segments
**Dependencies:** EXPORT-005
**Time:** 2 hours

### EXPORT-008: Create Export Manager
**Acceptance Criteria:**
- Function to export all formats
- Parse format string (json,srt)
- Call appropriate exporters
**Technical Notes:** Return list of created files
**Dependencies:** EXPORT-003, EXPORT-005
**Time:** 3 hours

---

## Sprint 5: CLI Foundation (10 tickets)

### CLI-001: Setup Typer App
**Acceptance Criteria:**
- Create cli.py with Typer instance
- Add app = typer.Typer()
- Configure help text
**Technical Notes:** Use pretty_exceptions_enable=False
**Dependencies:** SETUP-004
**Time:** 2 hours

### CLI-002: Create Main Entry Point
**Acceptance Criteria:**
- Add if __name__ == "__main__" block
- Call app() to run CLI
- Handle KeyboardInterrupt
**Technical Notes:** Catch and handle gracefully
**Dependencies:** CLI-001
**Time:** 2 hours

### CLI-003: Add Version Command
**Acceptance Criteria:**
- Add --version flag
- Read version from pyproject.toml
- Display with rich formatting
**Technical Notes:** Use importlib.metadata
**Dependencies:** CLI-001
**Time:** 3 hours

### CLI-004: Setup Logging Module
**Acceptance Criteria:**
- Create logging.py
- Configure rich console
- Set up log levels
**Technical Notes:** Use rich.console.Console
**Dependencies:** SETUP-004
**Time:** 3 hours

### CLI-005: Add Verbose Flag
**Acceptance Criteria:**
- Global --verbose flag
- Set log level accordingly
- Apply to all commands
**Technical Notes:** Use callback for global options
**Dependencies:** CLI-004
**Time:** 3 hours

### CLI-006: Create Transcribe Command Stub
**Acceptance Criteria:**
- Add @app.command() for transcribe
- Accept URL parameter
- Print placeholder message
**Technical Notes:** Type hints for parameters
**Dependencies:** CLI-001
**Time:** 2 hours

### CLI-007: Add Basic Parameters
**Acceptance Criteria:**
- Add --engine, --model flags
- Add --output-dir option
- Include help text for each
**Technical Notes:** Use typer.Option()
**Dependencies:** CLI-006
**Time:** 3 hours

### CLI-008: Implement Parameter Validation
**Acceptance Criteria:**
- Validate engine choices (whisper only for now)
- Check output directory exists
- Validate URL format
**Technical Notes:** Raise typer.BadParameter
**Dependencies:** CLI-007
**Time:** 3 hours

### CLI-009: Add Progress Display
**Acceptance Criteria:**
- Show status messages with rich
- Use spinners for long operations
- Clear, informative output
**Technical Notes:** Use rich.status
**Dependencies:** CLI-004
**Time:** 3 hours

### CLI-010: Create Cache Command Stubs
**Acceptance Criteria:**
- Add cache command group
- Stub ls and clear subcommands
- Placeholder implementations
**Technical Notes:** Use @app.command(name="cache")
**Dependencies:** CLI-001
**Time:** 2 hours

---

## Sprint 6: Basic Whisper Engine (12 tickets)

### WHISPER-001: Create Engines Package
**Acceptance Criteria:**
- Create engines/ folder
- Add __init__.py
- Create base.py for interface
**Technical Notes:** Define abstract interface
**Dependencies:** SETUP-003
**Time:** 2 hours

### WHISPER-002: Define Engine Interface
**Acceptance Criteria:**
- Abstract base class TranscriptionEngine
- Define transcribe() method signature
- Include configuration handling
**Technical Notes:** Use typing.Protocol
**Dependencies:** WHISPER-001, MODEL-002
**Time:** 3 hours

### WHISPER-003: Create Whisper Engine Module
**Acceptance Criteria:**
- Create whisper_engine.py
- Import faster-whisper
- Basic class structure
**Technical Notes:** Handle import errors gracefully
**Dependencies:** WHISPER-002
**Time:** 2 hours

### WHISPER-004: Implement Model Loading
**Acceptance Criteria:**
- Load faster-whisper model
- Cache loaded models
- Handle model download
**Technical Notes:** Use WhisperModel class
**Dependencies:** WHISPER-003
**Time:** 4 hours

### WHISPER-005: Add Model Size Validation
**Acceptance Criteria:**
- Validate model name (tiny to large-v3-turbo)
- Provide helpful error for invalid models
- Set appropriate defaults
**Technical Notes:** Default to large-v3-turbo
**Dependencies:** WHISPER-004
**Time:** 2 hours

### WHISPER-006: Configure Compute Type
**Acceptance Criteria:**
- Set compute_type based on device
- Default int8 for CPU/Apple Silicon
- Allow override via config
**Technical Notes:** Check platform.system()
**Dependencies:** WHISPER-004
**Time:** 3 hours

### WHISPER-007: Implement Basic Transcription
**Acceptance Criteria:**
- Call model.transcribe() method
- Process audio file input
- Return segments generator
**Technical Notes:** Use vad_filter=True
**Dependencies:** WHISPER-004
**Time:** 4 hours

### WHISPER-008: Add Batched Inference
**Acceptance Criteria:**
- Enable batch_size=8 parameter
- Verify performance improvement
- Handle batch processing
**Technical Notes:** Requires faster-whisper 1.0+
**Dependencies:** WHISPER-007
**Time:** 3 hours

### WHISPER-009: Convert to Segment Models
**Acceptance Criteria:**
- Convert Whisper segments to TranscriptSegment
- Extract all available fields
- Handle missing confidence scores
**Technical Notes:** Use getattr for optional fields
**Dependencies:** WHISPER-007, MODEL-002
**Time:** 3 hours

### WHISPER-010: Add Language Detection
**Acceptance Criteria:**
- Auto-detect language if not specified
- Return detected language code
- Set in transcript metadata
**Technical Notes:** Use detect_language() method
**Dependencies:** WHISPER-007
**Time:** 3 hours

### WHISPER-011: Implement Progress Callback
**Acceptance Criteria:**
- Show transcription progress
- Update rich progress bar
- Estimate time remaining
**Technical Notes:** Use callback parameter
**Dependencies:** WHISPER-007, CLI-009
**Time:** 3 hours

### WHISPER-012: Wire Up Basic Pipeline
**Acceptance Criteria:**
- Connect CLI to downloader to Whisper
- Full end-to-end test
- Export JSON and SRT files
**Technical Notes:** Minimal error handling for now
**Dependencies:** All previous
**Time:** 4 hours

---

## Deliverables Checklist

### End of Phase 1 Capabilities:
- [ ] Project properly initialized with uv
- [ ] All dependencies installed and locked
- [ ] Basic CLI with transcribe command
- [ ] YouTube video download working
- [ ] Audio normalization to WAV
- [ ] Whisper transcription functional
- [ ] JSON and SRT export working
- [ ] Basic progress indication
- [ ] Environment configuration

### Success Criteria:
- Run: `uv run ytx transcribe https://youtu.be/[video-id] --engine whisper`
- Produces: transcript.json and captions.srt files
- Works with videos up to 10 minutes
- Clear error messages for common issues

### Known Limitations (Phase 2 items):
- No Gemini integration yet
- No caching system
- No chapter support
- No summarization
- Limited error recovery
- No comprehensive tests

---

## Notes for Developers

1. **Each ticket is independent**: Can be assigned to different developers
2. **Time estimates are conservative**: Include testing and documentation
3. **Dependencies are explicit**: Follow the dependency chain
4. **Regular integration**: Merge completed tickets frequently
5. **Documentation as you go**: Update README with each feature

## Phase 1 Timeline

- **Week 1**: Project Setup & Core Models (18 tickets)
- **Week 2**: Downloader & Audio Processing (12 tickets)
- **Week 3**: Exporters & CLI Foundation (18 tickets)
- **Week 4**: Whisper Engine & Integration (12 tickets)
- **Buffer**: 1 week for integration and bug fixes

Total: 5 weeks for full Phase 1 completion with single developer
With 2 developers: ~2.5 weeks
With team of 4: ~1.5 weeks
