import json
from pathlib import Path

from handfont_orchestrator.pilot import build_pilot_outputs


def _write(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def test_build_pilot_outputs(tmp_path: Path):
    _write(tmp_path / "run-report.json", {
        "status": "review",
        "data_origin": "synthetic",
        "truth_note": "합성 데이터",
        "font_policy": {"remaining_font_binaries": 0},
    })
    _write(tmp_path / "01-preflight" / "preflight-report.json", {
        "selected_pages": [1, 2, 3],
        "selected": {
            "1": {"status": "accept"},
            "2": {"status": "review"},
            "3": {"status": "accept"},
        },
    })
    records = []
    for index in range(1, 106):
        records.append({"cell_id": f"C{index}", "raster_iou": 0.93})
    _write(tmp_path / "02-ingest" / "session-summary.json", {
        "selected_pages": [1, 2, 3],
        "cell_status_counts": {"ok": 103, "too_dense": 2},
        "vectorization": {"records": records},
    })
    for page in (1, 2, 3):
        cells = []
        for index in range(1, 36):
            status = "too_dense" if page == 3 and index in (34, 35) else "ok"
            cells.append({
                "cell_id": f"P{page:02d}-C{index:02d}",
                "character": "가",
                "unicode": "U+AC00",
                "quality": {"status": status, "ink_ratio": 0.08, "foreground_pixels": 1000},
            })
        _write(tmp_path / "02-ingest" / "pages" / f"page-{page:02d}" / "metadata.json", {
            "input": {"template_page": page},
            "cells": cells,
        })
    result = build_pilot_outputs(tmp_path, (1, 2, 3))
    assert result["pilot_status"] == "ready-for-full-capture"
    assert result["metrics"]["page_identification_ratio"] == 1.0
    assert result["metrics"]["rewrite_count"] == 2
    assert (tmp_path / "pilot-report.html").exists()
    assert (tmp_path / "rewrite-priority.csv").exists()


def test_pilot_blocks_missing_page(tmp_path: Path):
    _write(tmp_path / "run-report.json", {
        "status": "stopped",
        "data_origin": "real",
        "truth_note": "실제 데이터",
        "font_policy": {"remaining_font_binaries": 0},
    })
    _write(tmp_path / "01-preflight" / "preflight-report.json", {"selected_pages": [1, 3], "selected": {}})
    _write(tmp_path / "02-ingest" / "session-summary.json", {
        "selected_pages": [1, 3], "cell_status_counts": {}, "vectorization": {"records": []}
    })
    result = build_pilot_outputs(tmp_path, (1, 2, 3))
    assert result["pilot_status"] == "blocked"
    assert result["metrics"]["missing_pages"] == [2]
