from __future__ import annotations

"""Segment stitching and de-duplication across chunk boundaries.

Merges overlapping or duplicate segments while preserving time continuity.
"""

from typing import List
import difflib

from .models import TranscriptSegment


def _normalize_text(s: str) -> str:
    return " ".join(s.lower().strip().split())


def _similar(a: str, b: str, *, threshold: float = 0.8) -> bool:
    if not a or not b:
        return False
    if a in b or b in a:
        return True
    return difflib.SequenceMatcher(None, a, b).ratio() >= threshold


def _merge_text_dedup(a: str, b: str) -> str:
    a_s = a.strip()
    b_s = b.strip()
    al = a_s.lower()
    bl = b_s.lower()
    if not a_s:
        return b_s
    if not b_s:
        return a_s
    if al in bl:
        return b_s
    if bl in al:
        return a_s
    # Suffix-prefix overlap merge
    max_k = min(len(a_s), len(b_s))
    for k in range(max_k, 0, -1):
        if a_s.endswith(b_s[:k]):
            return a_s + b_s[k:]
    # Default: join with space
    return a_s + " " + b_s


def stitch_segments(segments: List[TranscriptSegment], *, epsilon: float = 0.01) -> List[TranscriptSegment]:
    """Merge overlapping/duplicate segments and ensure monotonic timelines.

    - If two consecutive segments overlap and their texts are highly similar,
      merges them into a single segment (deduping text overlap).
    - Otherwise trims the overlap by moving the next segment's start to the
      previous end.
    """
    if not segments:
        return []
    # Work on a sorted copy
    segs = sorted(segments, key=lambda s: (float(s.start), float(s.end)))
    out: List[TranscriptSegment] = []
    for s in segs:
        if not out:
            out.append(TranscriptSegment(id=0, start=float(s.start), end=float(s.end), text=s.text, confidence=s.confidence))
            continue
        last = out[-1]
        # Overlap check
        if float(s.start) <= float(last.end) + epsilon:
            a = _normalize_text(last.text)
            b = _normalize_text(s.text)
            if _similar(a, b):
                # Merge into last
                merged_text = _merge_text_dedup(last.text, s.text)
                last.text = merged_text
                last.end = max(float(last.end), float(s.end))
                continue
            # No textual similarity: trim overlap
            start = max(float(s.start), float(last.end))
            out.append(TranscriptSegment(id=0, start=start, end=float(s.end) if float(s.end) > start else start + 0.001, text=s.text, confidence=s.confidence))
        else:
            out.append(TranscriptSegment(id=0, start=float(s.start), end=float(s.end), text=s.text, confidence=s.confidence))
    # Renumber ids
    for i, s in enumerate(out):
        s.id = i
    return out


__all__ = [
    "stitch_segments",
]

