import json
from pathlib import Path

import numpy as np
import cv2

from handfont_orchestrator.manifests import build_captured_manifest, export_representative_masks, merge_manifests


def _write_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def test_build_and_merge_manifests(tmp_path: Path):
    ingest = tmp_path / "ingest"
    vector = ingest / "vectors" / "P01-C01"
    vector.mkdir(parents=True)
    (vector / "glyph.svg").write_text("<svg xmlns='http://www.w3.org/2000/svg' width='10' height='10'><path d='M1 1L9 1L9 9Z'/></svg>", encoding="utf-8")
    _write_json(vector / "metadata.json", {"summary": {"contours": 1}})
    _write_json(ingest / "session-summary.json", {
        "vectorization": {"records": [{"cell_id": "P01-C01", "character": "A", "svg": "vectors/P01-C01/glyph.svg"}]}
    })
    first = ingest / "captured.json"
    result = build_captured_manifest(ingest, first)
    assert result["glyph_count"] == 1
    second_dir = tmp_path / "second"
    second_dir.mkdir()
    (second_dir / "b.svg").write_text((vector / "glyph.svg").read_text(), encoding="utf-8")
    _write_json(second_dir / "b.json", {"summary": {"contours": 1}})
    second = second_dir / "manifest.json"
    _write_json(second, {"glyphs": [{"character": "B", "codepoint": 66, "svg": "b.svg", "metadata": "b.json", "category": "generated"}]})
    combined = tmp_path / "out" / "combined.json"
    merged = merge_manifests([first, second], combined)
    assert merged["glyph_count"] == 2
    assert [item["character"] for item in merged["glyphs"]] == ["A", "B"]


def test_export_representative_masks(tmp_path: Path):
    ingest = tmp_path / "ingest"
    page = ingest / "pages" / "page-01"
    mask = page / "cells" / "P01-C01" / "ink-mask.png"
    mask.parent.mkdir(parents=True)
    cv2.imwrite(str(mask), np.full((20, 20), 255, dtype=np.uint8))
    _write_json(page / "metadata.json", {"cells": [{"character": "가", "files": {"ink_mask": "cells/P01-C01/ink-mask.png"}}]})
    position_map = tmp_path / "position.json"
    _write_json(position_map, {"entries": [{"character": "가"}]})
    result = export_representative_masks(ingest, position_map, tmp_path / "masks")
    assert result["copied"] == 1
    assert (tmp_path / "masks" / "U+AC00.png").exists()
