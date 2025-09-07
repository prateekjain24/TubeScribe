from ytx.chapters import parse_yt_dlp_chapters


def test_parse_yt_dlp_chapters_infer_end():
    meta = {
        "duration": 120,
        "chapters": [
            {"title": "Intro", "start_time": 0},
            {"title": "Main", "start_time": 60, "end_time": 120},
        ]
    }
    chs = parse_yt_dlp_chapters(meta, video_duration=120)
    assert len(chs) == 2
    assert chs[0].end == 60
    assert chs[1].start == 60 and chs[1].end == 120

