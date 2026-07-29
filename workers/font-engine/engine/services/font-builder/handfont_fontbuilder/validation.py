from __future__ import annotations

import json
import math
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from fontTools.ttLib import TTFont


ASCII_SAMPLE_LINES = [
    "HAND FONT STUDIO 2026",
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
    "abcdefghijklmnopqrstuvwxyz",
    "0123456789  !? @#& +=% $₩",
    "The quick brown fox jumps over 13 lazy dogs.",
]


def _hangul_lines(cmap: dict[int, str]) -> list[str]:
    available = [chr(cp) for cp in sorted(cmap) if 0xAC00 <= cp <= 0xD7A3]
    if not available:
        return []
    chunks = ["".join(available[i : i + 18]) for i in range(0, min(len(available), 90), 18)]
    return chunks


def _sample_lines(cmap: dict[int, str]) -> list[str]:
    hangul = _hangul_lines(cmap)
    if hangul:
        ascii_supported = all(ord(ch) in cmap for ch in "HandFont2026")
        return hangul + (["HandFont Studio 2026"] if ascii_supported else [])
    return ASCII_SAMPLE_LINES


def _render_specimen(font_path: Path, output_dir: Path, lines: list[str]) -> tuple[Path, int]:
    width = 1800
    line_height = 104
    image = Image.new("L", (width, 50 + line_height * len(lines)), 255)
    draw = ImageDraw.Draw(image)
    title_font = ImageFont.truetype(str(font_path), 64)
    body_font = ImageFont.truetype(str(font_path), 54)
    y = 24
    nonempty_lines = 0
    for index, line in enumerate(lines):
        font_obj = title_font if index == 0 else body_font
        before_bytes = image.tobytes()
        draw.text((35, y), line, font=font_obj, fill=0)
        if image.tobytes() != before_bytes:
            nonempty_lines += 1
        y += line_height
    specimen_path = output_dir / "font-specimen.png"
    image.save(specimen_path)
    return specimen_path, nonempty_lines


def _render_glyph_grid(font_path: Path, codepoints: list[int], output_dir: Path) -> tuple[Path, list[str]]:
    columns = 12
    tile_width = 130
    tile_height = 145
    rows = math.ceil(len(codepoints) / columns)
    canvas = Image.new("L", (columns * tile_width, rows * tile_height), 255)
    draw = ImageDraw.Draw(canvas)
    glyph_font = ImageFont.truetype(str(font_path), 76)
    label_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
    empty: list[str] = []
    for index, codepoint in enumerate(codepoints):
        character = chr(codepoint)
        col = index % columns
        row = index // columns
        x0 = col * tile_width
        y0 = row * tile_height
        tile = Image.new("L", (tile_width, 106), 255)
        tile_draw = ImageDraw.Draw(tile)
        bbox = tile_draw.textbbox((0, 0), character, font=glyph_font)
        width = bbox[2] - bbox[0]
        height = bbox[3] - bbox[1]
        x = (tile_width - width) / 2 - bbox[0]
        y = (100 - height) / 2 - bbox[1]
        tile_draw.text((x, y), character, font=glyph_font, fill=0)
        ink_pixels = sum(tile.histogram()[:240])
        if ink_pixels == 0:
            empty.append(f"U+{codepoint:04X}")
        canvas.paste(tile, (x0, y0))
        label = f"U+{codepoint:04X}"
        label_bbox = draw.textbbox((0, 0), label, font=label_font)
        label_x = x0 + (tile_width - (label_bbox[2] - label_bbox[0])) / 2
        draw.text((label_x, y0 + 116), label, font=label_font, fill=60)
    path = output_dir / "glyph-grid.png"
    canvas.save(path)
    return path, empty


def validate_and_render(font_path: Path, output_dir: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    font = TTFont(font_path, recalcBBoxes=False, recalcTimestamp=False, checkChecksums=2)
    cmap = font.getBestCmap() or {}
    lines = _sample_lines(cmap)
    required = [ord(ch) for line in lines for ch in line if ch != " "]
    missing_sample_codepoints = sorted(set(required).difference(cmap))
    glyf = font["glyf"]
    hmtx = font["hmtx"].metrics
    empty_outlines: list[str] = []
    metric_violations: list[dict] = []
    hangul_width_violations: list[dict] = []
    for codepoint, glyph_name in sorted(cmap.items()):
        if codepoint == 0x20:
            continue
        glyph = glyf[glyph_name]
        if glyph.numberOfContours == 0:
            empty_outlines.append(f"U+{codepoint:04X}")
            continue
        advance, lsb = hmtx[glyph_name]
        if glyph.xMin != lsb or advance - glyph.xMax < 0:
            metric_violations.append(
                {
                    "codepoint": f"U+{codepoint:04X}",
                    "glyph": glyph_name,
                    "xMin": glyph.xMin,
                    "xMax": glyph.xMax,
                    "lsb": lsb,
                    "advance": advance,
                    "computed_rsb": advance - glyph.xMax,
                }
            )
        if 0xAC00 <= codepoint <= 0xD7A3 and advance != 1000:
            hangul_width_violations.append({"codepoint": f"U+{codepoint:04X}", "advance": advance})

    report = {
        "fonttools_load": True,
        "checksum_validation": True,
        "tables": sorted(font.keys()),
        "glyph_order_count": len(font.getGlyphOrder()),
        "cmap_count": len(cmap),
        "hangul_cmap_count": sum(0xAC00 <= cp <= 0xD7A3 for cp in cmap),
        "units_per_em": font["head"].unitsPerEm,
        "sample_lines": lines,
        "sample_missing_codepoints": [f"U+{codepoint:04X}" for codepoint in missing_sample_codepoints],
        "empty_outlines": empty_outlines,
        "metric_violations": metric_violations,
        "hangul_width_violations": hangul_width_violations,
        "font_bbox": [font["head"].xMin, font["head"].yMin, font["head"].xMax, font["head"].yMax],
    }
    font.close()

    fc_scan_path = output_dir / "fc-scan.txt"
    try:
        result = subprocess.run(["fc-scan", str(font_path)], check=True, capture_output=True, text=True, timeout=20)
        fc_scan_path.write_text(result.stdout, encoding="utf-8")
        report["fc_scan"] = True
    except (OSError, subprocess.SubprocessError) as exc:
        fc_scan_path.write_text(str(exc), encoding="utf-8")
        report["fc_scan"] = False

    specimen_path, nonempty_lines = _render_specimen(font_path, output_dir, lines)
    encoded_codepoints = sorted(codepoint for codepoint in cmap if codepoint != 0x20)
    grid_path, empty_rendered = _render_glyph_grid(font_path, encoded_codepoints, output_dir)
    report["pillow_load"] = True
    report["rendered_nonempty_lines"] = nonempty_lines
    report["empty_rendered_glyphs"] = empty_rendered
    report["specimen"] = specimen_path.name
    report["glyph_grid"] = grid_path.name
    (output_dir / "font-validation.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report
