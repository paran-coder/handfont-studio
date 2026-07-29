from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from handfont_vectorizer.io import write_image
from handfont_vectorizer.models import VectorizeOptions
from handfont_vectorizer.pipeline import vectorize_mask


FONT_CANDIDATES = [
    Path("/usr/share/fonts/truetype/unfonts-extra/UnPenheulim.ttf"),
    Path("/usr/share/fonts/truetype/nanum/NanumGothic.ttf"),
    Path("/usr/share/fonts/truetype/unfonts-core/UnDotum.ttf"),
]
SAMPLES = [
    ("hangul-ga", "가", "한글"),
    ("hangul-han", "한", "한글"),
    ("hangul-glyph", "글", "한글"),
    ("latin-A", "A", "영문 대문자"),
    ("latin-g", "g", "영문 소문자"),
    ("digit-8", "8", "숫자"),
    ("symbol-amp", "&", "기호"),
]


def find_font() -> Path:
    for path in FONT_CANDIDATES:
        if path.exists():
            return path
    raise SystemExit("벤치마크용 한글 글꼴을 찾지 못했습니다.")


def render_character(character: str, font_path: Path, size: int = 360) -> np.ndarray:
    image = Image.new("L", (size, size), 0)
    font = ImageFont.truetype(str(font_path), int(size * 0.64))
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


def contact_sheet(rows: list[tuple[str, np.ndarray, np.ndarray, np.ndarray]], output: Path, font_path: Path) -> None:
    tile = 240
    header = 40
    canvas = np.full((len(rows) * (tile + header), tile * 3, 3), 255, dtype=np.uint8)
    for row_index, (_, original, raster, difference) in enumerate(rows):
        y0 = row_index * (tile + header)
        for column, source in enumerate((original, raster, difference)):
            if source.ndim == 2:
                source = cv2.cvtColor(source, cv2.COLOR_GRAY2BGR)
            resized = cv2.resize(source, (tile, tile), interpolation=cv2.INTER_AREA)
            canvas[y0 + header : y0 + header + tile, column * tile : (column + 1) * tile] = resized

    pil_image = Image.fromarray(cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(pil_image)
    label_font = ImageFont.truetype(str(font_path), 20)
    for row_index, (name, _, _, _) in enumerate(rows):
        draw.text((10, row_index * (tile + header) + 8), name, fill=(20, 20, 20), font=label_font)
    canvas = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
    write_image(output, canvas)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--font", type=Path)
    args = parser.parse_args()
    output = args.output
    output.mkdir(parents=True, exist_ok=True)
    masks_dir = output / "masks"
    results_dir = output / "results"
    masks_dir.mkdir(exist_ok=True)
    results_dir.mkdir(exist_ok=True)
    font_path = args.font or find_font()

    records = []
    sheet_rows = []
    for slug, character, category in SAMPLES:
        mask = render_character(character, font_path)
        mask_path = write_image(masks_dir / f"{slug}.png", mask)
        result = vectorize_mask(
            mask_path,
            results_dir / slug,
            VectorizeOptions(simplify_tolerance=0.00085, corner_angle_degrees=110.0, smoothing_radius=0.05),
            title=f"{character} {slug}",
        )
        metadata = json.loads(result.metadata_path.read_text(encoding="utf-8"))
        raster = cv2.imread(str(result.raster_path), cv2.IMREAD_GRAYSCALE)
        difference = cv2.imread(str(result.difference_path), cv2.IMREAD_COLOR)
        sheet_rows.append((f"{character} / {slug}", mask, raster, difference))
        records.append({
            "slug": slug,
            "character": character,
            "category": category,
            "iou": result.iou,
            "contours": result.contour_count,
            "holes": metadata["summary"]["hole_contours"],
            "original_nodes": metadata["summary"]["original_nodes"],
            "simplified_nodes": metadata["summary"]["simplified_nodes"],
            "node_reduction_ratio": result.node_reduction_ratio,
            "path_commands": metadata["summary"]["path_commands"],
            "status": metadata["summary"]["status"],
        })

    summary = {
        "schema_version": "1.4.0",
        "font_used": str(font_path),
        "samples": len(records),
        "minimum_iou": min(item["iou"] for item in records),
        "mean_iou": sum(item["iou"] for item in records) / len(records),
        "minimum_node_reduction_ratio": min(item["node_reduction_ratio"] for item in records),
        "mean_node_reduction_ratio": sum(item["node_reduction_ratio"] for item in records) / len(records),
        "records": records,
    }
    (output / "benchmark-results.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    with (output / "benchmark-summary.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(records[0].keys()))
        writer.writeheader()
        writer.writerows(records)
    contact_sheet(sheet_rows, output / "comparison-sheet.png", font_path)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
