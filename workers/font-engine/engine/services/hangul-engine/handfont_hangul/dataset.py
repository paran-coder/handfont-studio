from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .decomposition import decompose_syllable
from .extraction import extract_position_regions


FONT_CANDIDATES = [
    Path("/usr/share/fonts/truetype/unfonts-extra/UnPenheulim.ttf"),
    Path("/usr/share/fonts/truetype/unfonts-extra/UnPilgia.ttf"),
    Path("/usr/share/fonts/truetype/nanum/NanumGothic.ttf"),
]


def find_reference_font() -> Path:
    for path in FONT_CANDIDATES:
        if path.exists():
            return path
    raise FileNotFoundError("한글 합성 PoC용 참조 글꼴을 찾지 못했습니다.")


def load_representative_syllables(csv_path: Path) -> list[dict[str, str]]:
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    result = [row for row in rows if row["category"] == "한글" and row["subgroup"] == "대표 음절"]
    if len(result) != 168:
        raise ValueError(f"대표 음절은 168자여야 합니다. 현재 {len(result)}자입니다.")
    return result


def render_character(character: str, font_path: Path, size: int = 480) -> np.ndarray:
    image = Image.new("L", (size, size), 0)
    font = ImageFont.truetype(str(font_path), int(size * 0.68))
    draw = ImageDraw.Draw(image)
    bbox = draw.textbbox((0, 0), character, font=font, stroke_width=1)
    width = bbox[2] - bbox[0]
    height = bbox[3] - bbox[1]
    x = (size - width) / 2 - bbox[0]
    y = (size - height) / 2 - bbox[1]
    draw.text((x, y), character, fill=255, font=font, stroke_width=1, stroke_fill=255)
    array = np.asarray(image, dtype=np.uint8)
    _, array = cv2.threshold(array, 32, 255, cv2.THRESH_BINARY)
    return array


def generate_dataset(output: Path, charset_csv: Path, vectorizer_root: Path, font_path: Path | None = None) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    masks_dir = output / "masks"
    glyphs_dir = output / "glyphs"
    components_dir = output / "position-regions"
    for path in (masks_dir, glyphs_dir, components_dir):
        path.mkdir(exist_ok=True)

    sys.path.insert(0, str(vectorizer_root))
    from handfont_vectorizer.io import write_image
    from handfont_vectorizer.models import VectorizeOptions
    from handfont_vectorizer.pipeline import vectorize_mask

    reference_font = font_path or find_reference_font()
    rows = load_representative_syllables(charset_csv)
    glyph_entries = []
    decomposition_entries = []
    failures = []

    for row in rows:
        character = row["character"]
        codepoint = ord(character)
        slug = f"U+{codepoint:04X}"
        mask = render_character(character, reference_font)
        mask_path = write_image(masks_dir / f"{slug}.png", mask)
        decomposition = extract_position_regions(character, mask, components_dir / slug)
        (components_dir / slug / "decomposition.json").write_text(
            json.dumps(decomposition, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        decomposition_entries.append(decomposition)
        try:
            result = vectorize_mask(
                mask_path,
                glyphs_dir / slug,
                VectorizeOptions(
                    minimum_component_area=4,
                    simplify_tolerance=0.0007,
                    corner_angle_degrees=112.0,
                    smoothing_radius=0.04,
                    minimum_foreground_ratio=0.00003,
                    target_raster_iou=0.90,
                    max_refinements=4,
                ),
                title=f"{character} {slug}",
            )
        except Exception as exc:
            failures.append({"character": character, "codepoint": slug, "error": str(exc)})
            continue
        d = decompose_syllable(character)
        glyph_entries.append(
            {
                "character": character,
                "codepoint": codepoint,
                "unicode": slug,
                "category": "한글",
                "subgroup": "대표 음절",
                "cell_id": row["cell_id"],
                "generation_role": row["generation_role"],
                "layout_class": d.layout_class,
                "svg": str(result.svg_path.relative_to(output)),
                "metadata": str(result.metadata_path.relative_to(output)),
                "mask": str(mask_path.relative_to(output)),
                "decomposition": str((components_dir / slug / "decomposition.json").relative_to(output)),
            }
        )

    manifest = {
        "schema_version": "1.6.0",
        "source_type": "synthetic-reference-font",
        "reference_font_name": reference_font.name,
        "requested_glyphs": len(rows),
        "generated_glyphs": len(glyph_entries),
        "failures": failures,
        "glyphs": glyph_entries,
    }
    (output / "hangul-glyph-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    decomp_map = {
        "schema_version": "1.6.0",
        "method": "unicode-decomposition-plus-overlapping-layout-regions",
        "entry_count": len(decomposition_entries),
        "entries": decomposition_entries,
    }
    (output / "hangul-position-map.json").write_text(json.dumps(decomp_map, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_decomposition_csv(output / "hangul-position-map.csv", decomposition_entries)
    return manifest


def _write_decomposition_csv(path: Path, entries: list[dict]) -> None:
    fields = [
        "character", "codepoint", "layout_class", "choseong", "jungseong", "jongseong",
        "choseong_form", "jungseong_form", "jongseong_form", "glyph_ink_bbox", "component_count",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for entry in entries:
            d = entry["decomposition"]
            writer.writerow(
                {
                    "character": entry["character"],
                    "codepoint": entry["codepoint"],
                    "layout_class": d["layout_class"],
                    "choseong": d["choseong"],
                    "jungseong": d["jungseong"],
                    "jongseong": d["jongseong"] or "",
                    "choseong_form": d["choseong_form"],
                    "jungseong_form": d["jungseong_form"],
                    "jongseong_form": d["jongseong_form"] or "",
                    "glyph_ink_bbox": ",".join(map(str, entry["glyph_ink_bbox"])),
                    "component_count": len(entry["components"]),
                }
            )
