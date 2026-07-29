from pathlib import Path

import cv2

from handfont_capture.field_synthetic import _add_glare
from handfont_capture.field_validation import FieldOptions, preflight_capture_session
from handfont_capture.synthetic import render_written_page, synthesize_capture


def _write(path: Path, image) -> Path:
    cv2.imwrite(str(path), image, [cv2.IMWRITE_JPEG_QUALITY, 92])
    return path


def test_preflight_accepts_clean_capture_and_writes_reports(tmp_path: Path):
    page = render_written_page(1, dpi=150, seed=101)
    capture, _ = synthesize_capture(page, seed=102, perspective=0.03, shadow=0.04, noise=1.0, jpeg_quality=94)
    photo = _write(tmp_path / "page-1.jpg", capture)
    output = tmp_path / "result"
    report = preflight_capture_session(
        [photo], output, FieldOptions(expected_pages=(1,), data_origin="synthetic")
    )
    assert report["session_status"] in {"accept", "review"}
    assert report["selected_pages"] == [1]
    assert report["data_origin"] == "synthetic"
    for name in ("preflight-report.json", "photo-results.csv", "retake-list.csv", "preflight-report.html", "preflight-overview.png"):
        assert (output / name).exists()


def test_preflight_blocks_hidden_marker(tmp_path: Path):
    page = render_written_page(1, dpi=150, seed=201)
    capture, markers = synthesize_capture(page, seed=202, perspective=0.05, shadow=0.08)
    x, y = markers[0].round().astype(int)
    radius = max(35, int(min(capture.shape[:2]) * 0.035))
    cv2.rectangle(capture, (x - radius, y - radius), (x + radius, y + radius), (246, 246, 246), -1)
    photo = _write(tmp_path / "blocked.jpg", capture)
    report = preflight_capture_session(
        [photo], tmp_path / "result", FieldOptions(expected_pages=(1,), data_origin="synthetic")
    )
    assert report["session_status"] == "blocked"
    assert report["photos"][0]["status"] == "blocked"
    assert "marker-failed" in report["photos"][0]["reasons"]


def test_preflight_marks_strong_glare_for_retake(tmp_path: Path):
    page = render_written_page(1, dpi=150, seed=301)
    capture, _ = synthesize_capture(page, seed=302, perspective=0.08, shadow=0.30, blur=3, noise=3.0, jpeg_quality=76)
    capture = _add_glare(capture, 0.095, seed=303)
    photo = _write(tmp_path / "glare.jpg", capture)
    report = preflight_capture_session(
        [photo], tmp_path / "result", FieldOptions(expected_pages=(1,), data_origin="synthetic")
    )
    assert report["photos"][0]["status"] in {"retake", "blocked"}


def test_missing_expected_page_blocks_session(tmp_path: Path):
    page = render_written_page(1, dpi=150, seed=401)
    capture, _ = synthesize_capture(page, seed=402, perspective=0.03, shadow=0.04)
    photo = _write(tmp_path / "page-1.jpg", capture)
    report = preflight_capture_session(
        [photo], tmp_path / "result", FieldOptions(expected_pages=(1, 2), data_origin="synthetic")
    )
    assert report["session_status"] == "blocked"
    assert report["missing_pages"] == [2]
