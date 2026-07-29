from __future__ import annotations

import json
import shutil
from pathlib import Path

from fontTools.ttLib import TTFont

from handfont_fontbuilder.builder import REQUIRED_TABLES, build_font
from handfont_fontbuilder.models import FontBuildOptions
from handfont_fontbuilder.validation import validate_and_render


PROJECT_ROOT = Path(__file__).resolve().parents[3]
BENCHMARK = PROJECT_ROOT / "services" / "glyph-vectorizer" / "examples" / "benchmark-v1.4.0" / "results"


def make_manifest(tmp_path: Path) -> Path:
    samples = [("A", "latin-A"), ("g", "latin-g"), ("8", "digit-8"), ("&", "symbol-amp")]
    entries = []
    for character, slug in samples:
        src = BENCHMARK / slug
        dst = tmp_path / slug
        shutil.copytree(src, dst)
        entries.append(
            {
                "character": character,
                "codepoint": ord(character),
                "category": "test",
                "svg": f"{slug}/glyph.svg",
                "metadata": f"{slug}/metadata.json",
            }
        )
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps({"glyphs": entries}), encoding="utf-8")
    return path


def test_build_and_reload_font(tmp_path: Path):
    manifest = make_manifest(tmp_path)
    output = tmp_path / "font"
    report = build_font(manifest, output, FontBuildOptions(family_name="HandFont Test"))
    font_path = output / report["font"]
    font = TTFont(font_path)
    assert font["head"].unitsPerEm == 1000
    assert REQUIRED_TABLES.issubset(font.keys())
    cmap = font.getBestCmap()
    assert cmap and all(ord(ch) in cmap for ch in "Ag8& ")
    assert report["missing_tables"] == []
    assert report["bounds_violations"] == []
    font.close()


def test_pillow_render(tmp_path: Path):
    manifest = make_manifest(tmp_path)
    output = tmp_path / "font"
    report = build_font(manifest, output, FontBuildOptions(family_name="HandFont Test"))
    validation = validate_and_render(output / report["font"], output)
    assert validation["fonttools_load"] is True
    assert validation["pillow_load"] is True
    assert validation["rendered_nonempty_lines"] >= 1
    assert (output / "font-specimen.png").exists()



def contour_areas(glyph, glyf_table):
    coordinates, end_points, _ = glyph.getCoordinates(glyf_table)
    areas = []
    start = 0
    for end in end_points:
        points = coordinates[start : end + 1]
        area = 0
        for i, point in enumerate(points):
            next_point = points[(i + 1) % len(points)]
            area += point[0] * next_point[1] - next_point[0] * point[1]
        areas.append(area / 2)
        start = end + 1
    return areas


def test_hole_winding_is_opposite(tmp_path: Path):
    manifest = make_manifest(tmp_path)
    output = tmp_path / "font"
    report = build_font(manifest, output, FontBuildOptions(family_name="HandFont Test"))
    font = TTFont(output / report["font"])
    cmap = font.getBestCmap()
    glyph = font["glyf"][cmap[ord("A")]]
    areas = contour_areas(glyph, font["glyf"])
    assert any(area > 0 for area in areas)
    assert any(area < 0 for area in areas)
    font.close()


def test_build_is_deterministic(tmp_path: Path):
    manifest = make_manifest(tmp_path)
    first = build_font(manifest, tmp_path / "one", FontBuildOptions(family_name="HandFont Test"))
    second = build_font(manifest, tmp_path / "two", FontBuildOptions(family_name="HandFont Test"))
    assert first["sha256"] == second["sha256"]


def test_os2_and_metrics_are_populated(tmp_path: Path):
    manifest = make_manifest(tmp_path)
    output = tmp_path / "font"
    report = build_font(manifest, output, FontBuildOptions(family_name="HandFont Test"))
    font = TTFont(output / report["font"])
    assert font["OS/2"].sCapHeight == 700
    assert font["OS/2"].sxHeight == 500
    assert font["OS/2"].ulCodePageRange1 & 1
    assert font["hhea"].ascent == 800
    assert font["hhea"].descent == -200
    font.close()


def test_full_poc_manifest_has_88_glyphs():
    manifest_path = Path(__file__).resolve().parents[1] / "examples" / "poc-source-v1.5.0" / "glyph-manifest.json"
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert data["requested_glyphs"] == 88
    assert data["generated_glyphs"] == 88
    assert data["failures"] == []
    assert len(data["glyphs"]) == 88
