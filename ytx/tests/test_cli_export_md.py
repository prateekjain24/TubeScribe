from pathlib import Path
from typer.testing import CliRunner


def _write_doc_json(path: Path):
    from ytx.models import TranscriptDoc, TranscriptSegment, Chapter, Summary
    doc = TranscriptDoc(
        video_id="VID12345678",
        source_url="https://youtu.be/VID12345678",
        title="Title",
        duration=65.0,
        language="en",
        engine="whisper",
        model="small",
        segments=[TranscriptSegment(id=0, start=0.0, end=0.5, text="Hello")],
        chapters=[Chapter(title="Intro", start=0.0, end=60.0)],
        summary=Summary(tldr="Short summary", bullets=["Point A", "Point B"]),
    )
    Path(path).write_text(doc.model_dump_json(), encoding="utf-8")


def test_cli_export_from_file(tmp_path):
    # Arrange
    from_file = tmp_path / "doc.json"
    _write_doc_json(from_file)
    outdir = tmp_path / "notes"
    outdir.mkdir()

    # Act
    import importlib
    cli = importlib.import_module('ytx.cli')
    runner = CliRunner()
    res = runner.invoke(
        cli.app,
        [
            "export",
            "--from-file",
            str(from_file),
            "--to",
            "md",
            "--output-dir",
            str(outdir),
            "--md-frontmatter",
        ],
    )

    # Assert
    assert res.exit_code == 0, res.output
    md = outdir / "VID12345678.md"
    assert md.exists()
    txt = md.read_text(encoding="utf-8")
    assert txt.lstrip().startswith("---\n")
    assert "## Summary" in txt and "## Chapters" in txt

