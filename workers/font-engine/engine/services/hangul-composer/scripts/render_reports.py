from __future__ import annotations

import csv
import json
import math
from collections import defaultdict
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "examples" / "composition-benchmark-v1.7.0"
FONT_PATHS = [
    Path("/usr/share/fonts/truetype/nanum/NanumGothic.ttf"),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
]
FONT_PATH = next(path for path in FONT_PATHS if path.exists())


def load_rows() -> list[dict]:
    with (OUTPUT / "benchmark-results.csv").open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    numeric = {
        "index", "exact_components", "fallback_components", "aligned_iou", "normalized_chamfer",
        "density_ratio", "density_log_error", "max_pair_overlap_ratio", "generated_ink_pixels",
        "reference_ink_pixels", "quality_score", "vector_iou", "vector_contours", "node_reduction_ratio",
    }
    for row in rows:
        for key in numeric:
            row[key] = float(row[key])
        row["overflow"] = row["overflow"].lower() == "true"
    return rows


def render_comparison(rows: list[dict], filename: str, title: str) -> None:
    columns = 4
    tile_w = 390
    tile_h = 250
    rows_count = math.ceil(len(rows) / columns)
    canvas = Image.new("RGB", (columns * tile_w, 70 + rows_count * tile_h), "white")
    draw = ImageDraw.Draw(canvas)
    title_font = ImageFont.truetype(str(FONT_PATH), 28)
    label_font = ImageFont.truetype(str(FONT_PATH), 17)
    small_font = ImageFont.truetype(str(FONT_PATH), 14)
    draw.text((24, 18), title, fill="black", font=title_font)
    for index, row in enumerate(rows):
        col = index % columns
        grid_row = index // columns
        x0 = col * tile_w
        y0 = 70 + grid_row * tile_h
        slug = row["codepoint"]
        item = OUTPUT / "generated" / slug
        generated = Image.open(item / "composed-mask.png").convert("L")
        reference = Image.open(item / "reference-mask.png").convert("L")
        generated.thumbnail((155, 155))
        reference.thumbnail((155, 155))
        tile = Image.new("RGB", (tile_w, tile_h), "white")
        td = ImageDraw.Draw(tile)
        gx = 20 + (155 - generated.width) // 2
        gy = 44 + (155 - generated.height) // 2
        rx = 212 + (155 - reference.width) // 2
        ry = 44 + (155 - reference.height) // 2
        tile.paste(Image.merge("RGB", (generated, generated, generated)), (gx, gy))
        tile.paste(Image.merge("RGB", (reference, reference, reference)), (rx, ry))
        td.rectangle((12, 36, 183, 208), outline=(170, 170, 170), width=1)
        td.rectangle((204, 36, 375, 208), outline=(170, 170, 170), width=1)
        td.text((18, 8), f"{row['character']}  {slug}", fill="black", font=label_font)
        td.text((55, 211), "조합", fill="black", font=small_font)
        td.text((247, 211), "참조", fill="black", font=small_font)
        td.text(
            (18, 230),
            f"IoU {row['aligned_iou']:.3f} · 점수 {row['quality_score']:.1f} · fallback {int(row['fallback_components'])}",
            fill="black",
            font=small_font,
        )
        canvas.paste(tile, (x0, y0))
    canvas.save(OUTPUT / filename, optimize=True)


def stats(values: list[float]) -> dict:
    values = sorted(values)
    if not values:
        return {"count": 0}
    def pct(p: float) -> float:
        position = (len(values) - 1) * p
        lo = int(math.floor(position))
        hi = int(math.ceil(position))
        if lo == hi:
            return values[lo]
        return values[lo] * (hi - position) + values[hi] * (position - lo)
    return {
        "count": len(values),
        "minimum": round(values[0], 6),
        "p10": round(pct(0.1), 6),
        "median": round(pct(0.5), 6),
        "mean": round(sum(values) / len(values), 6),
        "p90": round(pct(0.9), 6),
        "maximum": round(values[-1], 6),
    }


def write_breakdown(rows: list[dict]) -> None:
    by_layout: dict[str, list[dict]] = defaultdict(list)
    by_resolution: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_layout[row["layout_class"]].append(row)
        by_resolution["fallback" if row["fallback_components"] else "exact-only"].append(row)

    def summarize(group: list[dict]) -> dict:
        return {
            "count": len(group),
            "review_count": sum(row["status"] == "review" for row in group),
            "aligned_iou": stats([row["aligned_iou"] for row in group]),
            "quality_score": stats([row["quality_score"] for row in group]),
            "vector_iou": stats([row["vector_iou"] for row in group]),
            "density_ratio": stats([row["density_ratio"] for row in group]),
            "max_pair_overlap_ratio": stats([row["max_pair_overlap_ratio"] for row in group]),
        }

    data = {
        "schema_version": "1.7.0",
        "by_layout": {key: summarize(value) for key, value in sorted(by_layout.items())},
        "by_resolution": {key: summarize(value) for key, value in sorted(by_resolution.items())},
    }
    (OUTPUT / "quality-breakdown.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    rows = load_rows()
    render_comparison(sorted(rows, key=lambda row: (row["quality_score"], row["aligned_iou"]))[:24], "comparison-worst-24.png", "검수 우선 24자 — 조합 결과와 참조")
    render_comparison(sorted(rows, key=lambda row: (-row["quality_score"], -row["aligned_iou"]))[:24], "comparison-best-24.png", "품질 상위 24자 — 조합 결과와 참조")
    write_breakdown(rows)
