from ytx.downloader import extract_video_id, _friendly_yt_dlp_error


def test_extract_video_id_variants():
    assert extract_video_id("https://www.youtube.com/watch?v=ABCDEFGHIJK") == "ABCDEFGHIJK"
    assert extract_video_id("https://youtu.be/ABCDEFGHIJK") == "ABCDEFGHIJK"
    assert extract_video_id("https://www.youtube.com/shorts/ABCDEFGHIJK") == "ABCDEFGHIJK"
    assert extract_video_id("ABCDEFGHIJK") == "ABCDEFGHIJK"
    assert extract_video_id("https://example.com/foo") is None


def test_friendly_error_hints():
    e = _friendly_yt_dlp_error("This video is age-restricted", "url")
    assert "cookies" in e.lower()
    e2 = _friendly_yt_dlp_error("this video is private", "url")
    assert "private" in e2.lower()

