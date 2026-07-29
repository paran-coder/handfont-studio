from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path

from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFont

SERVICE_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = SERVICE_ROOT.parents[1]
FONT_BUILDER_ROOT = PROJECT_ROOT / "services" / "font-builder"
sys.path.insert(0, str(SERVICE_ROOT))
sys.path.insert(0, str(FONT_BUILDER_ROOT))

from handfont_fontbuilder.builder import build_font  # noqa: E402
from handfont_fontbuilder.models import FontBuildOptions  # noqa: E402
from handfont_hangul.decomposition import compose_syllable, decompose_syllable  # noqa: E402


COLORS = {
    "choseong": (230, 70, 70),
    "jungseong": (50, 150, 90),
    "jongseong": (55, 105, 210),
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def make_region_sheet(source_dir: Path, output_path: Path, position_map: dict) -> None:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for entry in position_map["entries"]:
        grouped[entry["decomposition"]["layout_class"]].append(entry)
    layout_order = [
        "vertical-open", "vertical-final", "horizontal-open",
        "horizontal-final", "compound-open", "compound-final",
    ]
    samples = []
    for layout in layout_order:
        samples.extend(grouped[layout][:2])

    tile_w, tile_h = 330, 350
    canvas = Image.new("RGB", (tile_w * 4, tile_h * 3), "white")
    label_font_path = "/usr/share/fonts/truetype/nanum/NanumGothic.ttf"
    label_font = ImageFont.truetype(label_font_path, 24)
    small_font = ImageFont.truetype(label_font_path, 16)
    for index, entry in enumerate(samples):
        col, row = index % 4, index // 4
        x0, y0 = col * tile_w, row * tile_h
        cp = ord(entry["character"])
        mask = Image.open(source_dir / "masks" / f"U+{cp:04X}.png").convert("L")
        bbox = mask.getbbox()
        if bbox is None:
            continue
        crop = mask.crop(bbox)
        crop.thumbnail((250, 245))
        tile = Image.new("RGB", (tile_w, tile_h), "white")
        px = (tile_w - crop.width) // 2
        py = 48 + (245 - crop.height) // 2
        tile.paste(Image.merge("RGB", (crop, crop, crop)), (px, py))
        draw = ImageDraw.Draw(tile, "RGBA")
        gx0, gy0, gx1, gy1 = entry["glyph_ink_bbox"]
        source_w, source_h = max(1, gx1 - gx0), max(1, gy1 - gy0)
        scale_x = crop.width / source_w
        scale_y = crop.height / source_h
        for comp in entry["components"]:
            rx0, ry0, rx1, ry1 = comp["pixel_region"]
            box = (
                px + int((rx0 - gx0) * scale_x),
                py + int((ry0 - gy0) * scale_y),
                px + int((rx1 - gx0) * scale_x),
                py + int((ry1 - gy0) * scale_y),
            )
            color = COLORS[comp["role"]]
            draw.rectangle(box, outline=color + (230,), width=3)
        d = entry["decomposition"]
        draw.text((18, 12), f"{entry['character']}  {d['layout_class']}", font=label_font, fill=(20, 20, 20, 255))
        parts = f"{d['choseong']} + {d['jungseong']}" + (f" + {d['jongseong']}" if d["jongseong"] else "")
        draw.text((18, 318), parts, font=small_font, fill=(50, 50, 50, 255))
        canvas.paste(tile, (x0, y0))
    canvas.save(output_path)


def validate(source_dir: Path, font_dir: Path, output_path: Path) -> dict:
    manifest = json.loads((source_dir / "hangul-glyph-manifest.json").read_text(encoding="utf-8"))
    position_map = json.loads((source_dir / "hangul-position-map.json").read_text(encoding="utf-8"))
    build_report = json.loads((font_dir / "font-build-report.json").read_text(encoding="utf-8"))
    font_validation = json.loads((font_dir / "font-validation.json").read_text(encoding="utf-8"))
    font_path = font_dir / build_report["font"]

    metadata = []
    for glyph in manifest["glyphs"]:
        metadata.append(json.loads((source_dir / glyph["metadata"]).read_text(encoding="utf-8")))
    ious = [item["summary"]["raster_iou"] for item in metadata]
    reductions = [item["summary"]["node_reduction_ratio"] for item in metadata]

    roundtrip_failures = []
    for item in position_map["entries"]:
        d = item["decomposition"]
        recomposed = compose_syllable(d["choseong"], d["jungseong"], d["jongseong"])
        if recomposed != item["character"]:
            roundtrip_failures.append({"character": item["character"], "recomposed": recomposed})

    layout_counts = Counter(item["decomposition"]["layout_class"] for item in position_map["entries"])
    position_forms = set()
    empty_regions = []
    for item in position_map["entries"]:
        d = item["decomposition"]
        position_forms.update(v for k, v in d.items() if k.endswith("_form") and v)
        for comp in item["components"]:
            if comp["ink_pixels"] <= 0:
                empty_regions.append({"character": item["character"], "role": comp["role"]})

    font = TTFont(font_path, recalcBBoxes=False, recalcTimestamp=False, checkChecksums=2)
    cmap = font.getBestCmap() or {}
    hmtx = font["hmtx"].metrics
    width_violations = []
    for cp, name in cmap.items():
        if 0xAC00 <= cp <= 0xD7A3 and hmtx[name][0] != 1000:
            width_violations.append({"codepoint": f"U+{cp:04X}", "advance": hmtx[name][0]})
    font.close()

    options = FontBuildOptions(
        family_name=build_report["family_name"],
        style_name=build_report["style_name"],
        output_basename=Path(build_report["font"]).stem,
    )
    with tempfile.TemporaryDirectory(prefix="handfont-v160-") as temp:
        second_report = build_font(source_dir / "hangul-glyph-manifest.json", Path(temp), options)
        deterministic = second_report["sha256"] == build_report["sha256"]

    report = {
        "schema_version": "1.6.0",
        "representative_syllables": manifest["generated_glyphs"],
        "dataset_failures": manifest["failures"],
        "unicode_roundtrip_failures": roundtrip_failures,
        "layout_class_counts": dict(sorted(layout_counts.items())),
        "position_region_count": sum(len(item["components"]) for item in position_map["entries"]),
        "unique_position_form_count": len(position_forms),
        "empty_position_regions": empty_regions,
        "vector_raster_iou": {
            "minimum": round(min(ious), 6),
            "mean": round(statistics.mean(ious), 6),
            "median": round(statistics.median(ious), 6),
            "maximum": round(max(ious), 6),
        },
        "node_reduction_ratio": {
            "minimum": round(min(reductions), 6),
            "mean": round(statistics.mean(reductions), 6),
            "maximum": round(max(reductions), 6),
        },
        "font": {
            "internal_filename": build_report["font"],
            "sha256": sha256(font_path),
            "glyph_count": build_report["glyph_count"],
            "mapped_codepoints": build_report["mapped_codepoints"],
            "hangul_cmap_count": font_validation["hangul_cmap_count"],
            "missing_tables": build_report["missing_tables"],
            "bounds_violations": build_report["bounds_violations"],
            "empty_outlines": font_validation["empty_outlines"],
            "metric_violations": font_validation["metric_violations"],
            "hangul_width_violations": width_violations,
            "empty_rendered_glyphs": font_validation["empty_rendered_glyphs"],
            "font_bbox": font_validation["font_bbox"],
            "unicode_range_bits": build_report["unicode_range_bits"],
            "codepage_range_bits": build_report["codepage_range_bits"],
            "deterministic_rebuild": deterministic,
        },
        "limitations": [
            "입력은 실제 사용자 필기가 아니라 참조 글꼴을 래스터화한 합성 데이터입니다.",
            "자모 위치 영역은 겹치는 레이아웃 휴리스틱이며 획 단위의 완전한 분할이 아닙니다.",
            "168개 대표 음절만 cmap에 포함하며 11,172개 전체 완성형 조합은 다음 단계입니다.",
        ],
    }
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    make_region_sheet(source_dir, output_path.parent / "position-region-sheet.png", position_map)
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--font-output", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = validate(args.source, args.font_output, args.output)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
