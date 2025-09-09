from ytx.downloader import _format_selector


def test_format_selector_with_cap():
    assert _format_selector(96) == "bestaudio[abr<=96]/bestaudio"
    assert _format_selector(128) == "bestaudio[abr<=128]/bestaudio"


def test_format_selector_disabled():
    assert _format_selector(None) == "bestaudio/best"
    assert _format_selector(0) == "bestaudio/best"

