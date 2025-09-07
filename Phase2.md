# Phase 2: Advanced Features & Optimization

## Overview

Phase 2 adds advanced capabilities including Gemini integration, intelligent caching, chapter processing, summarization, and production hardening.

**Duration**: ~65 tickets × 3 hours average = 195 hours (~5 weeks at full-time)
**Goal**: Production-ready tool with cloud transcription, caching, and advanced features

---

## Sprint 7: Caching System (10 tickets)

### CACHE-001: Create cache.py Module

**Acceptance Criteria:**

- Create cache.py with path utilities
- Define cache directory structure
- Use XDG standards for cache location
  **Technical Notes:** Default ~/.cache/ytx/
  **Dependencies:** Phase 1 complete
  **Time:** 2 hours
  **Status:** Done — Added `ytx/src/ytx/cache.py` with XDG-aware `cache_root()` and base helpers.

### CACHE-002: Implement Cache Path Builder

**Acceptance Criteria:**

- Generate paths based on video_id, engine, model
- Include config hash in path
- Create nested directory structure
  **Technical Notes:** video_id/engine/model/hash/
  **Dependencies:** CACHE-001
  **Time:** 3 hours
  **Status:** Done — Implemented `build_artifact_dir()` and `build_artifact_paths()` (video_id/engine/model/hash).

### CACHE-003: Add Cache Existence Check

**Acceptance Criteria:**

- Check if artifacts exist for config
- Verify file integrity
- Return boolean status
  **Technical Notes:** Check all expected files
  **Dependencies:** CACHE-002
  **Time:** 2 hours
  **Status:** Done — Added `artifacts_exist()`; verifies presence and non‑empty `transcript.json` and `captions.srt`.

### CACHE-004: Implement Artifact Reader

**Acceptance Criteria:**

- Load cached transcript.json
- Parse with orjson
- Return TranscriptDoc object
  **Technical Notes:** Handle corrupted cache
  **Dependencies:** CACHE-003
  **Time:** 3 hours
  **Status:** Done — Added `read_transcript_doc()` and `read_meta()` with typed errors.

### CACHE-005: Add Atomic Write Operations

**Acceptance Criteria:**

- Write to temp file first
- Atomic move to final location
- Handle concurrent writes
  **Technical Notes:** Use tempfile.NamedTemporaryFile
  **Dependencies:** CACHE-002
  **Time:** 3 hours
  **Status:** Done — Implemented `write_bytes_atomic()` and exporters already use atomic writes.

### CACHE-006: Create Cache Metadata

**Acceptance Criteria:**

- Write meta.json with cache info
- Include creation time, version
- Add source information
  **Technical Notes:** Track ytx version
  **Dependencies:** CACHE-005
  **Time:** 2 hours
  **Status:** Done — Added `build_meta_payload()` and `write_meta()` including created_at, ytx_version, and source.

### CACHE-007: Implement Cache List Command

**Acceptance Criteria:**

- List all cached transcripts
- Show video titles and dates
- Display cache size
  **Technical Notes:** Walk cache directory
  **Dependencies:** CACHE-001
  **Time:** 3 hours
  **Status:** Done — Added `ytx cache ls` using `scan_cache()` to show ID, engine/model, created date, size, and title.

### CACHE-008: Add Cache Clear Command

**Acceptance Criteria:**

- Clear all cache safely
- Option to clear specific video
- Confirmation prompt
  **Technical Notes:** Use shutil.rmtree carefully
  **Dependencies:** CACHE-007
  **Time:** 3 hours
  **Status:** Done — Added `ytx cache clear --yes [--video-id <id>]` backed by `clear_cache()` with size accounting.

### CACHE-009: Implement Cache Statistics

**Acceptance Criteria:**

- Calculate total cache size
- Count cached videos
- Show disk usage
  **Technical Notes:** Use os.stat for sizes
  **Dependencies:** CACHE-007
  **Time:** 2 hours
  **Status:** Done — Added `ytx cache stats` (entries, unique videos, total size) via `cache_statistics()`.

### CACHE-010: Add Cache Expiration

**Acceptance Criteria:**

- Optional TTL for cache entries
- Clean old entries on startup
- Configurable via environment
  **Technical Notes:** Default no expiration
  **Dependencies:** CACHE-006
  **Time:** 3 hours
  **Status:** Done — TTL via `YTX_CACHE_TTL_SECONDS`/`YTX_CACHE_TTL_DAYS`; startup runs `expire_cache(ttl)` when set.

---

## Sprint 8: Gemini Engine Core (15 tickets)

### GEMINI-001: Create Gemini Engine Module

**Acceptance Criteria:**

- Create gemini_engine.py
- Import google-generativeai
- Basic class structure
  **Technical Notes:** Handle missing API key
  **Dependencies:** WHISPER-002
  **Time:** 2 hours
  **Status:** Done — Added `engines/gemini_engine.py` with optional import and engine skeleton.

### GEMINI-002: Implement API Key Loading

**Acceptance Criteria:**

- Load GEMINI_API_KEY from environment
- Validate key format
- Clear error if missing
  **Technical Notes:** Use genai.configure()
  **Dependencies:** GEMINI-001
  **Time:** 2 hours
  **Status:** Done — Loads `GEMINI_API_KEY` (fallback `GOOGLE_API_KEY`), light validation, calls `genai.configure()`.

### GEMINI-003: Setup Model Configuration

**Acceptance Criteria:**

- Configure gemini-2.5-flash model
- Set generation parameters
- Handle model errors
  **Technical Notes:** Use GenerativeModel class
  **Dependencies:** GEMINI-002
  **Time:** 3 hours
  **Status:** Done — Uses `GenerativeModel('gemini-2.5-flash')` with conservative `generation_config` and error handling.

### GEMINI-004: Create Audio File Handler

**Acceptance Criteria:**

- Upload audio file to Gemini
- Handle file size limits
- Return file reference
  **Technical Notes:** Use genai.upload_file()
  **Dependencies:** GEMINI-003
  **Time:** 3 hours
  **Status:** Done — Implemented `_upload_audio()` using `genai.upload_file()` with MIME inference and a 2GB guard.

### GEMINI-005: Build Transcription Prompt

**Acceptance Criteria:**

- Create prompt for accurate transcription
- Request JSON format with timestamps
- Include formatting instructions
  **Technical Notes:** Specify exact JSON schema
  **Dependencies:** GEMINI-003
  **Time:** 3 hours
  **Status:** Done — Added `_build_prompt()` instructing strict JSON with segments [{start,end,text}] and optional language.

### GEMINI-006: Implement Basic Transcription

**Acceptance Criteria:**

- Send audio to Gemini
- Get transcription response
- Parse JSON output
  **Technical Notes:** Use generate_content()
  **Dependencies:** GEMINI-004, GEMINI-005
  **Time:** 4 hours
  **Status:** Done — Uploads audio, calls `generate_content([file, prompt])`, parses JSON segments or falls back to a single segment.

---

## Cross‑Provider Transcription Extensibility

To support OpenAI, Deepgram, and ElevenLabs cleanly, we adopt a small set of abstractions and CLI/config patterns that generalize across providers with different capabilities.

Architecture

- Cloud base: shared template for cloud engines
  - `setup_client(config)`: auth + client init
  - `prepare_input(path)`: upload or inline payload
  - `generate(payload)`: request with timeouts + retries
  - `parse_response(raw)`: normalize to `TranscriptSegment[]` (monotonic, clamped)
- Capabilities flags per engine
  - `has_native_segments`, `has_word_timestamps`, `has_diarization`, `supports_streaming`, `max_file_bytes`
  - Guides timestamp policy and error messaging
- Chunking + stitching modules
  - `fixed_window(seconds, overlap)` and `silence_based`
  - Helper to offset chunk segments and stitch overlaps

Config & CLI

- `engine_options` bag in config (env `YTX_ENGINE_OPTS` JSON) included in `config_hash()`
- Timestamp policy: `--timestamps {native,chunked,none}`
  - `native`: use provider segments/utterances when available (e.g., Deepgram/OpenAI)
  - `chunked`: force coarse timestamps via chunk offsets for text‑only providers (e.g., Gemini, ElevenLabs)
  - `none`: single text segment
- CLI: `--engine-opts '{"utterances":true,"diarize":true}'` forwarded to engines

Provider grounding

- OpenAI: Audio Transcriptions (multipart). Historically supports `response_format=verbose_json` with `segments` containing start/end seconds; treat as native when present, else fallback to chunked/none
- Deepgram: Native word/utterance timestamps and optional diarization; prefer `utterances` → segments, with options in `engine_options`
- ElevenLabs: Text‑first; timestamps/diarization availability varies; default to chunked or none
- Gemini: Best‑effort JSON timestamps; not guaranteed forced alignment; prefer `chunked` mode for reliable coarse timings

Cache & metadata

- Extend `meta.json` with `provider`, `request_id` (if available), and later `cost`/rate limit info
- Keep artifact layout unchanged; `engine_options` affects `config_hash()` for deterministic caching

Ticket notes

- Update GEMINI‑005/006/007 expectations: timestamps are best‑effort; engines must tolerate plain text and fallback to chunked or none according to policy
- Add OpenAI/Deepgram/ElevenLabs engine tickets later mirroring GEMINI structure, reusing the cloud base, and honoring `engine_options` + `--timestamps`

Implementation status

- Config: Added `timestamp_policy` and `engine_options` (env `YTX_ENGINE_OPTS`), included in `config_hash()`.
- CLI: Added `--timestamps {native,chunked,none}` and `--engine-opts` (JSON) flags.
- Cloud base: Introduced `engines/cloud_base.py` with retry helper; Gemini now extends this base.
- Meta: `meta.json` now includes `provider` (and optional `request_id` later).
- Engines: Gemini adapted to honor `timestamp_policy` (native/chunked/none) and reuse chunking/stitching.

### GEMINI-007: Add Response Parser

**Acceptance Criteria:**

- Parse Gemini JSON response
- Extract segments with timestamps
- Handle malformed responses
  **Technical Notes:** Use try/except for parsing
  **Dependencies:** GEMINI-006
  **Time:** 3 hours
  **Status:** Done — Added robust parser: strips code fences, tolerates alt keys (startTime/endTime), HH:MM:SS or numeric times, clamps monotonicity, and falls back to single segment if needed.

### GEMINI-008: Implement Audio Chunking

**Acceptance Criteria:**

- Split long audio into 5-10 min chunks
- Add 2 second overlaps
- Track chunk offsets
  **Technical Notes:** Use ffmpeg for splitting
  **Dependencies:** GEMINI-006
  **Time:** 4 hours
  **Status:** Done — Added `chunking.py` with `compute_chunks()` and `slice_wav_segment()` using ffmpeg; defaults 10m windows with 2s overlap.

### GEMINI-009: Add Chunk Processing Loop

**Acceptance Criteria:**

- Process each chunk sequentially
- Adjust timestamps by offset
- Collect all segments
  **Technical Notes:** Maintain order
  **Dependencies:** GEMINI-008
  **Time:** 3 hours
  **Status:** Done — Gemini engine processes chunks sequentially, offsets segment times by chunk start, and concatenates in order. Overlap de-dup is planned in GEMINI-010.

### GEMINI-010: Implement Segment Stitching

**Acceptance Criteria:**

- Merge overlapping segments
- Remove duplicate text
- Maintain time continuity
  **Technical Notes:** Compare overlap regions
  **Dependencies:** GEMINI-009
  **Time:** 4 hours
  **Status:** Done — Added `stitch_segments()` to merge duplicate/overlapping segments using text similarity and suffix/prefix de‑dup; trims overlaps to keep monotonic times.

### GEMINI-011: Add Rate Limit Handling

**Acceptance Criteria:**

- Detect rate limit errors
- Implement exponential backoff
- Use tenacity for retries
  **Technical Notes:** Max 3 retries
  **Dependencies:** GEMINI-006
  **Time:** 3 hours
  **Status:** Done — Wrapped `generate_content` with Tenacity (max 3 attempts, exponential backoff) and detect rate-limit via google.api_core exceptions or common 429/quota messages; non-rate errors fail fast.

### GEMINI-012: Implement Cost Estimation

**Acceptance Criteria:**

- Calculate token usage
- Estimate cost before processing
- Warn user if > $1
  **Technical Notes:** $0.30 per M tokens audio
  **Dependencies:** GEMINI-006
  **Time:** 3 hours

### GEMINI-013: Add Batch Mode Support

**Acceptance Criteria:**

- Enable batch API for 50% discount
- Handle async responses
- Implement polling
  **Technical Notes:** Optional via flag
  **Dependencies:** GEMINI-006
  **Time:** 4 hours

### GEMINI-014: Create Fallback Strategy

**Acceptance Criteria:**

- Fallback to Whisper on Gemini error
- Log fallback reason
- Notify user
  **Technical Notes:** Configurable behavior
  **Dependencies:** GEMINI-006
  **Time:** 3 hours
  **Status:** Done — Added CLI flag `--fallback` (default on). On Gemini errors, logs reason and transparently falls back to Whisper, exporting under the Whisper cache path.

### GEMINI-015: Wire Up Gemini Pipeline

**Acceptance Criteria:**

- Integrate with CLI
- Full end-to-end test
- Export results
  **Technical Notes:** Test with 5-min video
  **Dependencies:** GEMINI-001 to GEMINI-014
  **Time:** 3 hours
  **Status:** Done — CLI supports `--engine gemini` end-to-end (download → normalize → upload → transcribe → stitch → export). Fallback supported; outputs cached with meta.

---

## Sprint 9: Chapter Processing (10 tickets)

### CHAPTER-001: Create chapters.py Module

**Acceptance Criteria:**

- Create chapters module
- Define chapter utilities
- Import required libraries
  **Technical Notes:** Handle videos without chapters
  **Dependencies:** Phase 1 complete
  **Time:** 2 hours
  **Status:** Done — Added `ytx/src/ytx/chapters.py` with robust parsing helpers and graceful handling when absent.

### CHAPTER-002: Extract Chapter Metadata

**Acceptance Criteria:**

- Parse chapters from yt-dlp metadata
- Convert timestamps to seconds
- Validate chapter data
  **Technical Notes:** Some videos have auto-chapters
  **Dependencies:** CHAPTER-001
  **Time:** 3 hours
  **Status:** Done — `downloader._parse_metadata` now parses `chapters` using yt-dlp fields (`start_time`, `end_time`, `title`) and infers missing ends from next start or duration; `VideoMetadata` includes optional `chapters`.

### CHAPTER-003: Implement Audio Slicing

**Acceptance Criteria:**

- Slice audio by chapter boundaries
- Add configurable overlap (2s default)
- Save chapter segments
  **Technical Notes:** Use ffmpeg -ss and -t
  **Dependencies:** CHAPTER-002
  **Time:** 3 hours
  **Status:** Done — Implemented `slice_audio_by_chapters()` with 2s overlap default, writing 16kHz mono WAV per chapter via ffmpeg.

### CHAPTER-004: Add Chapter Processing Loop

**Acceptance Criteria:**

- Process each chapter independently
- Pass to transcription engine
- Track chapter index
  **Technical Notes:** Maintain chapter order
  **Dependencies:** CHAPTER-003
  **Time:** 3 hours
  **Status:** Done — Added `process_chapters()` to transcribe each chapter sequentially with progress and maintain order; offsets are handled in CHAPTER-005.

### CHAPTER-005: Implement Segment Offset Adjustment

**Acceptance Criteria:**

- Adjust timestamps to video time
- Add chapter start offset
- Maintain accuracy
  **Technical Notes:** Float precision important
  **Dependencies:** CHAPTER-004
  **Time:** 2 hours
  **Status:** Done — Added `offset_chapter_segments()` to shift per-chapter segments by chapter start into the global timeline, preserving precision and order.

### CHAPTER-006: Create Chapter-Aware Stitching

**Acceptance Criteria:**

- Merge segments across chapters
- Handle boundary overlaps
- Preserve chapter markers
  **Technical Notes:** Sort by timestamp
  **Dependencies:** CHAPTER-005
  **Time:** 3 hours
  **Status:** Done — Added `stitch_chapter_segments()` leveraging the global stitcher to merge overlap duplicates while leaving `TranscriptDoc.chapters` intact.

### CHAPTER-007: Add Chapter Metadata to Output

**Acceptance Criteria:**

- Include chapters in TranscriptDoc
- Add chapter titles and times
- Export in JSON
  **Technical Notes:** Optional field
  **Dependencies:** CHAPTER-006
  **Time:** 2 hours
  **Status:** Done — CLI now includes `meta.chapters` in `TranscriptDoc`, serialized to JSON exporters.

### CHAPTER-008: Implement Parallel Chapter Processing

**Acceptance Criteria:**

- Process chapters concurrently
- Limit parallelism to CPU count
- Maintain result order
  **Technical Notes:** Use ThreadPoolExecutor
  **Dependencies:** CHAPTER-004
  **Time:** 4 hours
  **Status:** Done — Added parallel processing via ThreadPoolExecutor (limited to CPU count) to transcribe per-chapter concurrently; results are sorted to maintain order.

### CHAPTER-009: Add Chapter Progress Display

**Acceptance Criteria:**

- Show progress per chapter
- Display chapter names
- Update overall progress
  **Technical Notes:** Use rich progress bars
  **Dependencies:** CHAPTER-008
  **Time:** 3 hours
  **Status:** Done — CLI shows per-chapter progress with chapter titles and an overall progress bar during chapter-based transcription.

### CHAPTER-010: Create Chapter Summary Option

**Acceptance Criteria:**

- Optional per-chapter summaries
- Use Gemini for summarization
- Add to chapter metadata
  **Technical Notes:** Only if --summarize
  **Dependencies:** CHAPTER-007
  **Time:** 3 hours
  **Status:** Done — Added `--summarize-chapters` flag. Uses a Gemini-based summarizer to produce concise per-chapter summaries and injects them into `TranscriptDoc.chapters[].summary`. Falls back gracefully if API key is missing.

---

## Sprint 10: Summarization Features (8 tickets)

### SUMMARY-001: Create Summary Module

**Acceptance Criteria:**

- Create summarizer.py
- Define summary functions
- Set up prompt templates
  **Technical Notes:** Use Gemini-2.5-flash for summaries
  **Dependencies:** GEMINI-015
  **Time:** 2 hours
  **Status:** Done — Added `ytx/src/ytx/summarizer.py` (GeminiSummarizer) with retry helpers and API key loading.

### SUMMARY-002: Build Summary Prompt

**Acceptance Criteria:**

- Create effective summary prompt
- Request TLDR and key points
- Specify output format
  **Technical Notes:** Max 500 chars for TLDR
  **Dependencies:** SUMMARY-001
  **Time:** 3 hours
  **Status:** Done — Structured prompt returns strict JSON: `{ tldr, bullets[] }` with length caps; plain-text fallback included.

### SUMMARY-003: Implement Transcript Summarization

**Acceptance Criteria:**

- Send transcript to Gemini
- Parse summary response
- Create Summary object
  **Technical Notes:** Handle long transcripts
  **Dependencies:** SUMMARY-002
  **Time:** 3 hours
  **Status:** Done — CLI `--summarize` computes overall summary, attaches to `TranscriptDoc.summary`, and writes `summary.json`.

### SUMMARY-004: Add Bullet Point Extraction

**Acceptance Criteria:**

- Extract 3-5 key points
- Format as bullet list
- Ensure conciseness
  **Technical Notes:** Each bullet < 100 chars
  **Dependencies:** SUMMARY-003
  **Time:** 3 hours
  **Status:** Done — Summarizer produces 3–5 concise bullets (<=100 chars) alongside TL;DR.

### SUMMARY-005: Implement Smart Truncation

**Acceptance Criteria:**

- Truncate long transcripts intelligently
- Maintain context for summary
- Use sliding window if needed
  **Technical Notes:** Max 100k tokens to Gemini
  **Dependencies:** SUMMARY-003
  **Time:** 3 hours
  **Status:** Done — Hierarchical summarization with ~4000-char windows and overlap; summarizes chunk TL;DRs into final.

### SUMMARY-006: Add Language-Aware Summaries

**Acceptance Criteria:**

- Detect transcript language
- Summarize in same language
- Handle multilingual content
  **Technical Notes:** Use detected language
  **Dependencies:** SUMMARY-003
  **Time:** 3 hours
  **Status:** Done — Prompts respect detected transcript language for TL;DR and bullets.

### SUMMARY-007: Create Summary Cache

**Acceptance Criteria:**

- Cache summaries separately
- Avoid re-summarizing
- Update if transcript changes
  **Technical Notes:** Include in config hash
  **Dependencies:** SUMMARY-003, CACHE-010
  **Time:** 2 hours
  **Status:** Done — Added `summary.json` artifact with read/write helpers; CLI populates from cache on `--summarize`.

### SUMMARY-008: Wire Up Summary Pipeline

**Acceptance Criteria:**

- Add --summarize flag to CLI
- Integrate with transcription
- Include in exports
  **Technical Notes:** Optional feature
  **Dependencies:** SUMMARY-001 to SUMMARY-007
  **Time:** 3 hours
  **Status:** Done — Added `--summarize` flag; integrates summaries into transcript JSON and exports.

---

## Sprint 11: Error Handling & Resilience (10 tickets)

### ERROR-001: Create Error Types

**Acceptance Criteria:**

- Define custom exception classes
- Include error codes
- Add user-friendly messages
  **Technical Notes:** Inherit from Exception
  **Dependencies:** None
**Time:** 2 hours
**Status:** Done — Added `ytx/src/ytx/errors.py` with `YTXError` base (codes/messages) and subclasses (Network/API/RateLimit/FileSystem/Timeout/etc.) plus `friendly_error()`.

### ERROR-002: Add Network Error Handling

**Acceptance Criteria:**

- Handle connection errors
- Implement retry logic
- Show clear messages
  **Technical Notes:** Use tenacity
  **Dependencies:** ERROR-001
**Time:** 3 hours
**Status:** Done — Cloud engines use Tenacity with rate-limit detection; downloader has retries/timeouts mapped to `TimeoutError`. CLI prints friendly API/network messages.

### ERROR-003: Implement File System Errors

**Acceptance Criteria:**

- Handle permission errors
- Check disk space
- Graceful degradation
  **Technical Notes:** Catch OSError
  **Dependencies:** ERROR-001
**Time:** 3 hours
**Status:** Done — Atomic writes wrap `OSError` → `FileSystemError`; ffmpeg/cache/engine errors now inherit `YTXError` for unified handling.

### ERROR-004: Add API Error Handling

**Acceptance Criteria:**

- Handle Gemini API errors
- Parse error responses
- Suggest solutions
  **Technical Notes:** Check quota limits
  **Dependencies:** ERROR-001
**Time:** 3 hours
**Status:** Done — Cloud base wraps non-rate exceptions into `APIError(provider=…)`; Gemini respects `transcribe_timeout`. CLI surfaces concise API messages.

### ERROR-005: Create Recovery Strategies

**Acceptance Criteria:**

- Define fallback options
- Implement partial recovery
- Save progress on failure
  **Technical Notes:** Write partial results
  **Dependencies:** ERROR-001
**Time:** 3 hours
**Status:** Done — Fallback to Whisper is implemented; on by-chapter failures, partial results are stitched and written to cache as a recovery step.

### ERROR-006: Add Input Validation

**Acceptance Criteria:**

- Validate all user inputs
- Check file formats
- Verify URL accessibility
  **Technical Notes:** Early validation
  **Dependencies:** ERROR-001
**Time:** 2 hours
**Status:** Done — Early URL/engine/model/output-dir checks; chapter mode warns when no chapters are present; dependencies checked on use with friendly guidance.

### ERROR-007: Implement Timeout Handling

**Acceptance Criteria:**

- Add timeouts to all operations
- Make configurable
- Handle gracefully
  **Technical Notes:** Default 5 min timeout
  **Dependencies:** ERROR-001
**Time:** 3 hours
**Status:** Done — Config adds timeouts (`network_timeout`, `download_timeout`, `transcribe_timeout`, `summarize_timeout`); downloader and Gemini calls honor them; errors are handled gracefully.

### ERROR-008: Create Error Reporting

**Acceptance Criteria:**

- Log errors with context
- Create error report file
- Sanitize sensitive data
  **Technical Notes:** Remove API keys
  **Dependencies:** ERROR-001
**Time:** 3 hours
**Status:** Done — Added sanitized error reports (`errors.write_error_report`) with timestamp, traceback, platform info, and redacted env; CLI writes reports on failures/interrupts.

### ERROR-009: Add Interrupt Handling

**Acceptance Criteria:**

- Handle Ctrl+C gracefully
- Clean up temp files
- Save progress if possible
  **Technical Notes:** Use signal handlers
  **Dependencies:** ERROR-005
**Time:** 3 hours
**Status:** Done — KeyboardInterrupt handling writes an error report; by-chapter path saves partial results when available; temp files are cleaned via context managers.

### ERROR-010: Implement Health Checks

**Acceptance Criteria:**

- Check ffmpeg availability
- Verify API keys
- Test network connectivity
  **Technical Notes:** Run before main operation
  **Dependencies:** ERROR-001
**Time:** 2 hours
**Status:** Done — Added `ytx health` command: checks ffmpeg availability, Gemini API key presence, and basic network connectivity.

---

## Sprint 12: Testing & Documentation (12 tickets)

### TEST-001: Setup Testing Framework

**Acceptance Criteria:**

- Configure pytest
- Add to pyproject.toml
- Create test structure
  **Technical Notes:** Use pytest-asyncio
  **Dependencies:** None
**Time:** 2 hours
**Status:** Done — Added pytest config in pyproject, conftest to include src/, and initial test suite.

### TEST-002: Create Test Fixtures

**Acceptance Criteria:**

- Sample audio files
- Mock API responses
- Test configurations
  **Technical Notes:** Use pytest fixtures
  **Dependencies:** TEST-001
  **Time:** 3 hours

### TEST-003: Write Model Tests

**Acceptance Criteria:**

- Test all Pydantic models
- Validation testing
- Serialization tests
  **Technical Notes:** 100% model coverage
  **Dependencies:** TEST-002
**Time:** 3 hours
**Status:** Done — Added unit tests for TranscriptSegment/TranscriptDoc (validation, JSON round‑trip).

### TEST-004: Add Downloader Tests

**Acceptance Criteria:**

- Mock yt-dlp responses
- Test error cases
- Verify retries
  **Technical Notes:** Use unittest.mock
  **Dependencies:** TEST-002
**Time:** 3 hours
**Status:** Done — Added tests for URL ID extraction and friendly yt‑dlp error hints.

### TEST-005: Create Engine Tests

**Acceptance Criteria:**

- Test Whisper engine
- Test Gemini engine
- Mock API calls
  **Technical Notes:** Test edge cases
  **Dependencies:** TEST-002
**Time:** 4 hours
**Status:** Done — Added mocked engine tests: WhisperEngine with fake model segments and GeminiEngine with stubbed upload + generate (JSON segments). No network or heavy deps.

### TEST-006: Write Integration Tests

**Acceptance Criteria:**

- End-to-end test with short audio
- Test all export formats
- Verify cache behavior
  **Technical Notes:** Use real 10s clip
  **Dependencies:** TEST-005
**Time:** 4 hours
**Status:** Done — Added integration test using Typer CliRunner with patched downloader/engine and a tiny generated WAV; verifies end‑to‑end JSON+SRT artifacts creation in cache.

### TEST-007: Add CLI Tests

**Acceptance Criteria:**

- Test all commands
- Verify parameter handling
- Check error messages
  **Technical Notes:** Use typer.testing
  **Dependencies:** TEST-001
**Time:** 3 hours
**Status:** Done — Added Typer CliRunner smoke tests for --version, hello, and health (with monkeypatched ffmpeg/network); also URL validation.

### TEST-008: Create Performance Tests

**Acceptance Criteria:**

- Benchmark transcription speed
- Memory usage monitoring
- Cache performance
  **Technical Notes:** Use pytest-benchmark
  **Dependencies:** TEST-006
**Time:** 3 hours
**Status:** Done — Added lightweight performance tests for chunk computation and SRT export timing; deterministic, offline, and fast.

### TEST-009: Write Comprehensive README

**Acceptance Criteria:**

- Installation instructions
- Usage examples
- Troubleshooting guide
  **Technical Notes:** Include screenshots
  **Dependencies:** None
**Time:** 3 hours
**Status:** Done — Updated root and ytx READMEs with install (venv/uv), local run (module form), new CLI flags, chapters/summaries, error handling, and health checks.

### TEST-010: Create API Documentation

**Acceptance Criteria:**

- Document all public APIs
- Include code examples
- Type hints complete
  **Technical Notes:** Use docstrings
  **Dependencies:** None
**Time:** 3 hours
**Status:** Done — Added `docs/API.md` with CLI overview, module references, models, and extension points.
**Status:** Pending — To add module overview and documented CLI/API usage.

### TEST-011: Add Configuration Guide

**Acceptance Criteria:**

- Document all env variables
- Explain configuration options
- Provide .env.example
  **Technical Notes:** Include defaults
  **Dependencies:** TEST-009
**Time:** 2 hours
**Status:** Done — Added `docs/CONFIG.md` covering env vars (YTX_*), CLI options, and `config_hash()` reproducibility.
**Status:** Pending — To document environment variables and config hashing.

### TEST-012: Create Release Checklist

**Acceptance Criteria:**

- Version bump process
- Testing requirements
- Release notes template
  **Technical Notes:** Include in README
  **Dependencies:** TEST-009
**Time:** 2 hours
**Status:** Done — Added `docs/RELEASE.md` with pre‑release, build/smoke test, tag/release, and post‑release steps.
**Status:** Pending — To add versioning, changelog, and release QA checklist.

---

## Sprint 13: Polish & Optimization (8 tickets)

### POLISH-001: Optimize Memory Usage

**Acceptance Criteria:**

- Profile memory consumption
- Reduce peak usage
- Stream large files
  **Technical Notes:** Use memory_profiler
  **Dependencies:** All features complete
  **Time:** 4 hours
  **Status:** Done — Reduced import-time memory footprint via lazy imports for heavy deps (faster‑whisper, google‑generativeai).

### POLISH-002: Improve Startup Time

**Acceptance Criteria:**

- Lazy load heavy imports
- Optimize model loading
- Cache precomputed data
  **Technical Notes:** Measure with time
  **Dependencies:** POLISH-001
  **Time:** 3 hours
  **Status:** Done — Avoid heavy imports at CLI import time; engines import dependencies on first use (lazy).

### POLISH-003: Add Colored Output

**Acceptance Criteria:**

- Use rich for all output
- Consistent color scheme
- Respect NO_COLOR env
  **Technical Notes:** Error=red, success=green
  **Dependencies:** None
  **Time:** 2 hours
  **Status:** Done — Health check output colors statuses (ok/present green, errors red, absent yellow); Rich styling elsewhere.

### POLISH-004: Enhance Progress Bars

**Acceptance Criteria:**

- Add ETA calculations
- Show transfer speeds
- Multiple progress bars
  **Technical Notes:** Use rich.progress
  **Dependencies:** POLISH-003
  **Time:** 3 hours
  **Status:** Done — Transcribe progress includes percentage alongside bar and ETA; download shows speed/ETA where available.

### POLISH-005: Create Debug Mode

**Acceptance Criteria:**

- Add --debug flag
- Verbose logging
- Save debug info
  **Technical Notes:** Include timings
  **Dependencies:** None
  **Time:** 2 hours
  **Status:** Done — Added global `--debug` to enable verbose logging and extra diagnostics.

### POLISH-006: Add Telemetry (Optional)

**Acceptance Criteria:**

- Anonymous usage stats
- Opt-in only
- Error tracking
  **Technical Notes:** Respect privacy
  **Dependencies:** None
  **Time:** 3 hours

### POLISH-007: Implement Update Check

**Acceptance Criteria:**

- Check for new versions
- Show update message
- Provide update command
  **Technical Notes:** Check GitHub releases
  **Dependencies:** None
  **Time:** 3 hours
  **Status:** Done — Added `ytx update-check` to compare local version with latest GitHub release and report status.

### POLISH-008: Final Integration Test

**Acceptance Criteria:**

- Test all features together
- Process 30-min video
- Verify all outputs
  **Technical Notes:** Full system test
  **Dependencies:** All previous
  **Time:** 4 hours

---

## Deliverables Checklist

### End of Phase 2 Capabilities:

- [ ] Complete caching system with persistence
- [ ] Gemini engine fully integrated
- [ ] Chapter-aware processing
- [ ] Automatic summarization
- [ ] Comprehensive error handling
- [ ] Full test coverage (>80%)
- [ ] Production-ready documentation
- [ ] Performance optimizations

### Success Criteria:

- Process videos up to 2 hours
- Support both Whisper and Gemini engines
- Intelligent caching reduces repeat processing
- Chapter support for structured videos
- Clear summaries in multiple languages
- Graceful handling of all error cases
- Comprehensive test suite passes
- Documentation suitable for open source release

### Performance Targets:

- Whisper: < 6x realtime on Apple Silicon
- Gemini: < 2 minutes for 30-min video
- Cache lookup: < 100ms
- Startup time: < 1 second
- Memory usage: < 2GB for 1-hour video

---

## Phase 2 Timeline

- **Week 1**: Caching System (10 tickets)
- **Week 2-3**: Gemini Engine (15 tickets)
- **Week 3**: Chapter Processing (10 tickets)
- **Week 4**: Summarization & Error Handling (18 tickets)
- **Week 5**: Testing, Documentation & Polish (20 tickets)
- **Buffer**: 1 week for integration and refinement

Total: 6 weeks for full Phase 2 completion with single developer
With 2 developers: ~3 weeks
With team of 4: ~2 weeks

---

## Risk Mitigation

### Technical Risks:

1. **Gemini API changes**: Abstract behind interface, version lock
2. **Rate limits**: Implement robust retry logic, batch mode
3. **Large file handling**: Streaming processing, chunking
4. **Memory constraints**: Profile and optimize, use generators

### Schedule Risks:

1. **Integration complexity**: Regular integration points
2. **Testing time**: Automate early, test continuously
3. **Documentation debt**: Document as you code
4. **Performance issues**: Profile early and often

---

## Definition of Done

Each ticket is complete when:

1. Code is written and working
2. Unit tests are passing
3. Integration verified
4. Documentation updated
5. Code reviewed (if team)
6. Merged to main branch

Phase 2 is complete when:

1. All tickets completed
2. Full test suite passing
3. Documentation complete
4. Performance targets met
5. Ready for v1.0 release

---

## Future Sprint: Cloud Engines (OpenAI, Deepgram, ElevenLabs)

### OPENAI-001: Create OpenAI Engine Module

**Acceptance Criteria:**

- Create `openai_engine.py` and register engine
- Optional import of OpenAI client or HTTP fallback
- Clear error on missing API key
  **Technical Notes:** Use `OPENAI_API_KEY` from environment
  **Dependencies:** Cloud base, chunking/stitching
  **Time:** 2 hours

### OPENAI-002: Implement API Key Loading & Client Setup

**Acceptance Criteria:**

- Load API key from env
- Initialize client with timeouts
- Fail fast with friendly error if misconfigured
  **Technical Notes:** Allow HTTP fallback if SDK absent
  **Dependencies:** OPENAI-001
  **Time:** 2 hours

### OPENAI-003: Setup Model Configuration

**Acceptance Criteria:**

- Choose default STT model (configurable via `model` or `engine_options`)
- Validate model name
- Map options from `engine_options`
  **Technical Notes:** Keep defaults provider-recommended; document overrides
  **Dependencies:** OPENAI-002
  **Time:** 2 hours

### OPENAI-004: Prepare Input (Multipart Upload)

**Acceptance Criteria:**

- Send audio as multipart file
- Handle size limits and timeouts
- Route to chunked strategy when oversized
  **Technical Notes:** Reuse `compute_chunks` and `slice_wav_segment`
  **Dependencies:** OPENAI-003
  **Time:** 3 hours

### OPENAI-005: Implement Basic Transcription

**Acceptance Criteria:**

- Call transcription endpoint with timeouts
- Apply rate-limit retries via cloud base
- Surface concise errors
  **Technical Notes:** Honor `timestamp_policy`
  **Dependencies:** OPENAI-004
  **Time:** 3 hours

### OPENAI-006: Add Response Parser

**Acceptance Criteria:**

- Parse response into segments when provider returns structured timings (e.g., verbose JSON)
- Fallback to single/chunked per `timestamp_policy`
- Clamp monotonic times
  **Technical Notes:** Tolerate plain text responses
  **Dependencies:** OPENAI-005
  **Time:** 3 hours

### OPENAI-007: Add Chunk Processing Loop

**Acceptance Criteria:**

- Process each chunk sequentially
- Offset timestamps by chunk start
- Stitch overlaps
  **Technical Notes:** Reuse `stitch_segments`
  **Dependencies:** OPENAI-006
  **Time:** 3 hours

### OPENAI-008: Wire Up CLI & Metadata

**Acceptance Criteria:**

- Enable `--engine openai`
- Support `--engine-opts` mapping
- Write `meta.provider` and `request_id` (if available)
  **Technical Notes:** Respect cache key via `engine_options`
  **Dependencies:** OPENAI-007
  **Time:** 2 hours

### DEEPGRAM-001: Create Deepgram Engine Module

**Acceptance Criteria:**

- Create `deepgram_engine.py` and register engine
- Optional import of SDK or HTTP fallback
- Clear error on missing API key
  **Technical Notes:** Use `DEEPGRAM_API_KEY` from environment
  **Dependencies:** Cloud base, chunking/stitching
  **Time:** 2 hours

### DEEPGRAM-002: Implement Client & Options

**Acceptance Criteria:**

- Initialize client with timeouts
- Map `engine_options` (e.g., model, smart_format, utterances, diarize)
- Validate options
  **Technical Notes:** Document recommended defaults
  **Dependencies:** DEEPGRAM-001
  **Time:** 2 hours

### DEEPGRAM-003: Implement Pre-recorded Transcription Call

**Acceptance Criteria:**

- Upload audio or send by URL
- Add retries for rate limits
- Handle size/length limits with chunk fallback
  **Technical Notes:** Honor `timestamp_policy`
  **Dependencies:** DEEPGRAM-002
  **Time:** 3 hours

### DEEPGRAM-004: Add Response Parser

**Acceptance Criteria:**

- Prefer utterances for segments (start/end, text)
- Fallback to word timings if utterances absent
- Clamp and sanitize segments
  **Technical Notes:** Defer diarization to future tickets
  **Dependencies:** DEEPGRAM-003
  **Time:** 3 hours

### DEEPGRAM-005: Add Chunk Processing Loop

**Acceptance Criteria:**

- Process chunks, offset times, stitch overlaps
- Preserve order and continuity
- Log per-chunk progress
  **Technical Notes:** Reuse shared utilities
  **Dependencies:** DEEPGRAM-004
  **Time:** 3 hours

### DEEPGRAM-006: Wire Up CLI & Metadata

**Acceptance Criteria:**

- Enable `--engine deepgram`
- Accept `--engine-opts` mapping
- Write `meta.provider` and any request identifiers
  **Technical Notes:** Cache paths include engine options
  **Dependencies:** DEEPGRAM-005
  **Time:** 2 hours

### ELEVEN-001: Create ElevenLabs Engine Module

**Acceptance Criteria:**

- Create `eleven_engine.py` and register engine
- Optional import of SDK or HTTP fallback
- Clear error on missing API key
  **Technical Notes:** Use `ELEVENLABS_API_KEY` from environment
  **Dependencies:** Cloud base, chunking/stitching
  **Time:** 2 hours

### ELEVEN-002: Implement Client & Model Options

**Acceptance Criteria:**

- Initialize client with timeouts
- Map `engine_options` to model/params
- Validate model setting
  **Technical Notes:** Document limitations of timestamp support
  **Dependencies:** ELEVEN-001
  **Time:** 2 hours

### ELEVEN-003: Implement Basic Transcription

**Acceptance Criteria:**

- Upload audio and get transcript
- Apply retries for rate limits
- Fallback to chunked/none per `timestamp_policy`
  **Technical Notes:** Timeouts and clear errors
  **Dependencies:** ELEVEN-002
  **Time:** 3 hours

### ELEVEN-004: Add Response Parser

**Acceptance Criteria:**

- Parse transcript; if timestamps provided, convert to segments
- Otherwise fallback to chunked or none
- Ensure monotonic times
  **Technical Notes:** Tolerate partial/empty fields
  **Dependencies:** ELEVEN-003
  **Time:** 3 hours

### ELEVEN-005: Add Chunk Processing Loop

**Acceptance Criteria:**

- Process chunks, offset times, stitch overlaps
- Preserve order and continuity
- Log progress
  **Technical Notes:** Reuse shared utilities
  **Dependencies:** ELEVEN-004
  **Time:** 3 hours

### ELEVEN-006: Wire Up CLI & Metadata

**Acceptance Criteria:**

- Enable `--engine elevenlabs`
- Accept `--engine-opts` mapping
- Write `meta.provider` and identifiers (if any)
  **Technical Notes:** Cache separation via `engine_options`
  **Dependencies:** ELEVEN-005
  **Time:** 2 hours
