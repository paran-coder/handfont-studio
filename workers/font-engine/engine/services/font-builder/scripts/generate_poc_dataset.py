from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

SERVICE_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = SERVICE_ROOT.parents[1]
VECTORIZER_ROOT = PROJECT_ROOT / "services" / "glyph-vectorizer"
sys.path.insert(0, str(VECTORIZER_ROOT))

from handfont_vectorizer.io import write_image  # noqa: E402
from handfont_vectorizer.models import VectorizeOptions  # noqa: E402
from handfont_vectorizer.pipeline import vectorize_mask  # noqa: E402


FONT_CANDIDATES = [
    Path("/usr/share/fonts/truetype/unfonts-extra/UnPenheulim.ttf"),
    Path("/usr/share/fonts/truetype/nanum/NanumGothic.ttf"),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
]


def find_font() -> Path:
    for path in FONT_CANDIDATES:
        if path.exists():
            return path
    raise SystemExit("PoC 입력 생성용 글꼴을 찾지 못했습니다.")


def load_charset(csv_path: Path) -> list[dict[str, str]]:
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    return [row for row in rows if row["category"] in {"영문", "숫자", "기호"}]


def render_character(character: str, font_path: Path, size: int = 420) -> np.ndarray:
    image = Image.new("L", (size, size), 0)
    font = ImageFont.truetype(str(font_path), int(size * 0.67))
    draw = ImageDraw.Draw(image)
    bbox = draw.textbbox((0, 0), character, font=font, stroke_width=1)
    width = bbox[2] - bbox[0]
    height = bbox[3] - bbox[1]
    x = (size - width) / 2 - bbox[0]
    y = (size - height) / 2 - bbox[1]
    draw.text((x, y), character, fill=255, font=font, stroke_width=1, stroke_fill=255)
    array = np.array(image, dtype=np.uint8)
    _, array = cv2.threshold(array, 32, 255, cv2.THRESH_BINARY)
    return array


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--font", type=Path)
    parser.add_argument("--charset", type=Path, default=PROJECT_ROOT / "character-set-v1.3.0.csv")
    args = parser.parse_args()

    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    masks_dir = output / "masks"
    glyphs_dir = output / "glyphs"
    masks_dir.mkdir(exist_ok=True)
    glyphs_dir.mkdir(exist_ok=True)
    font_path = args.font or find_font()
    rows = load_charset(args.charset)
    glyph_entries = []
    failures = []

    for row in rows:
        character = row["character"]
        codepoint = ord(character)
        slug = f"U+{codepoint:04X}"
        mask = render_character(character, font_path)
        mask_path = write_image(masks_dir / f"{slug}.png", mask)
        try:
            result = vectorize_mask(
                mask_path,
                glyphs_dir / slug,
                VectorizeOptions(
                    minimum_component_area=4,
                    simplify_tolerance=0.00075,
                    corner_angle_degrees=110.0,
                    smoothing_radius=0.045,
                    minimum_foreground_ratio=0.00003,
                    target_raster_iou=0.89,
                    max_refinements=4,
                ),
                title=f"{character} {slug}",
            )
        except Exception as exc:  # PoC generation report must retain every failed codepoint.
            failures.append({"character": character, "codepoint": slug, "error": str(exc)})
            continue
        glyph_entries.append(
            {
                "character": character,
                "codepoint": codepoint,
                "unicode": slug,
                "category": row["category"],
                "subgroup": row["subgroup"],
                "cell_id": row["cell_id"],
                "svg": str(result.svg_path.relative_to(output)),
                "metadata": str(result.metadata_path.relative_to(output)),
                "mask": str(mask_path.relative_to(output)),
            }
        )

    manifest = {
        "schema_version": "1.5.0",
        "source_type": "synthetic-reference-font",
        "reference_font": str(font_path),
        "requested_glyphs": len(rows),
        "generated_glyphs": len(glyph_entries),
        "failures": failures,
        "glyphs": glyph_entries,
    }
    (output / "glyph-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({key: manifest[key] for key in ("requested_glyphs", "generated_glyphs", "failures")}, ensure_ascii=False, indent=2))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
