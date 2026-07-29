import json
from pathlib import Path

import cv2

from handfont_capture.models import SessionOptions
from handfont_capture.session import process_capture_session
from handfont_capture.synthetic import render_written_page, synthesize_capture


def test_three_page_session_with_duplicate_and_manual_fallback(tmp_path: Path):
    photos = tmp_path / "photos"
    photos.mkdir()
    manual = {}
    for page in (1, 2, 3):
        written = render_written_page(page, dpi=150, seed=100)
        image, markers = synthesize_capture(written, seed=200 + page, perspective=0.05, jpeg_quality=88)
        name = f"capture-{page}.jpg"
        if page == 2:
            center = tuple(markers[0].round().astype(int))
            cv2.rectangle(image, (center[0] - 45, center[1] - 45), (center[0] + 45, center[1] + 45), (246, 246, 246), -1)
            manual[name] = markers.tolist()
        cv2.imwrite(str(photos / name), image)
    poor, _ = synthesize_capture(render_written_page(1, dpi=150, seed=101), seed=999, blur=7, noise=8.0, jpeg_quality=50)
    cv2.imwrite(str(photos / "capture-1-duplicate.jpg"), poor)
    manual_path = tmp_path / "manual.json"
    manual_path.write_text(json.dumps({"files": manual}), encoding="utf-8")

    summary = process_capture_session(
        [photos],
        tmp_path / "output",
        SessionOptions(dpi=150, expected_pages=(1, 2, 3), vectorize=False, min_page_confidence=0.2),
        manual_corners_path=manual_path,
    )
    assert summary["complete"] is True
    assert summary["selected_pages"] == [1, 2, 3]
    assert summary["manual_pages"] == [2]
    assert summary["duplicate_pages"] == [1]
    assert summary["failed_inputs"] == 0
