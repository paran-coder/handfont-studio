from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "hangul-source-v1.6.0"


def test_generated_manifest_has_168_syllables():
    data = json.loads((EXAMPLE / "hangul-glyph-manifest.json").read_text(encoding="utf-8"))
    assert data["requested_glyphs"] == 168
    assert data["generated_glyphs"] == 168
    assert data["failures"] == []
    assert len(data["glyphs"]) == 168
    assert len({item["codepoint"] for item in data["glyphs"]}) == 168


def test_position_map_has_no_empty_regions():
    data = json.loads((EXAMPLE / "hangul-position-map.json").read_text(encoding="utf-8"))
    assert data["entry_count"] == 168
    assert sum(len(item["components"]) for item in data["entries"]) == 447
    assert all(component["ink_pixels"] > 0 for item in data["entries"] for component in item["components"])
