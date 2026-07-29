from __future__ import annotations

import json
from pathlib import Path

import pytest

from handfont_fontbuilder.errors import ManifestError
from handfont_fontbuilder.manifest import load_manifest


def write_manifest(tmp_path: Path, glyphs: list[dict]) -> Path:
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps({"glyphs": glyphs}), encoding="utf-8")
    return path


def test_rejects_duplicate_codepoints(tmp_path: Path):
    svg = tmp_path / "g.svg"
    meta = tmp_path / "m.json"
    svg.write_text("x", encoding="utf-8")
    meta.write_text("{}", encoding="utf-8")
    manifest = write_manifest(tmp_path, [
        {"character": "A", "codepoint": 65, "svg": "g.svg", "metadata": "m.json"},
        {"character": "A", "codepoint": 65, "svg": "g.svg", "metadata": "m.json"},
    ])
    with pytest.raises(ManifestError, match="중복"):
        load_manifest(manifest)


def test_rejects_mismatched_codepoint(tmp_path: Path):
    svg = tmp_path / "g.svg"
    meta = tmp_path / "m.json"
    svg.write_text("x", encoding="utf-8")
    meta.write_text("{}", encoding="utf-8")
    manifest = write_manifest(tmp_path, [
        {"character": "A", "codepoint": 66, "svg": "g.svg", "metadata": "m.json"},
    ])
    with pytest.raises(ManifestError, match="일치"):
        load_manifest(manifest)


def test_rejects_missing_input_files(tmp_path: Path):
    manifest = write_manifest(tmp_path, [
        {"character": "A", "codepoint": 65, "svg": "missing.svg", "metadata": "missing.json"},
    ])
    with pytest.raises(ManifestError, match="없습니다"):
        load_manifest(manifest)
