from ytx.exporters.utils import seconds_to_hhmmss, youtube_url, safe_md


def test_seconds_to_hhmmss_zero_and_subsecond():
    assert seconds_to_hhmmss(0.0) == "0:00"
    assert seconds_to_hhmmss(0.9) == "0:00"
    assert seconds_to_hhmmss(59.9) == "0:59"


def test_seconds_to_hhmmss_minute_and_hour():
    assert seconds_to_hhmmss(83.5) == "1:23"  # floor semantics
    assert seconds_to_hhmmss(3600.0) == "1:00:00"
    assert seconds_to_hhmmss(3661.2) == "1:01:01"


def test_youtube_url_styles_and_time():
    vid = "ABCDEFGHIJK"
    assert youtube_url(vid, None) == f"https://youtu.be/{vid}"
    assert youtube_url(vid, 0) == f"https://youtu.be/{vid}"
    assert youtube_url(vid, 83.9) == f"https://youtu.be/{vid}?t=83"
    assert youtube_url(vid, 83.9, style="long") == f"https://www.youtube.com/watch?v={vid}&t=83"


def test_safe_md_minimal():
    s = "*hi_ [link] code(`x`)"
    out = safe_md(s)
    # ensure characters are escaped
    assert "\\*hi\\_ \\[link\\]" in out

