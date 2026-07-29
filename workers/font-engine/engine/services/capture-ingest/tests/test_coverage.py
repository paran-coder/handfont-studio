from pathlib import Path

from handfont_capture.coverage import analyze_position_coverage
from handfont_capture.compat import HANGUL_ENGINE_ROOT


def test_position_coverage_reports_missing_provider():
    metadata = [{
        "cells": [
            {"cell_id": "P01-C01", "character": "가", "quality": {"status": "missing", "foreground_ratio": 0.0}},
            {"cell_id": "P01-C02", "character": "까", "quality": {"status": "ok", "foreground_ratio": 0.1}},
        ]
    }]
    result = analyze_position_coverage(
        metadata,
        HANGUL_ENGINE_ROOT / "examples" / "hangul-source-v1.6.0" / "hangul-position-map.json",
    )
    assert result["expected_position_forms"] == 175
    assert result["missing_position_forms"] > 0
    assert result["rewrite_candidates"][0]["priority"] >= 0
