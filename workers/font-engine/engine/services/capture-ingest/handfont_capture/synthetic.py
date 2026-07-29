from __future__ import annotations

import csv
import json
import math
import random
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .compat import IMAGE_PIPELINE_ROOT  # noqa: F401
from handfont_pipeline.cells import normalized_box_to_pixels, relative_roi_to_pixels
from handfont_pipeline.config import DEFAULT_BLANK_DIR, DEFAULT_LAYOUT_PATH, DEFAULT_MAPPING_PATH, load_cells, load_layout
from handfont_pipeline.perspective import canonical_size, destination_markers

DEFAULT_FONT = Path("/usr/share/fonts/truetype/unfonts-extra/UnPilgia.ttf")
FALLBACK_FONT = Path("/usr/share/fonts/truetype/nanum/NanumGothic.ttf")


def _mapping_by_page(mapping_path: Path | str = DEFAULT_MAPPING_PATH) -> dict[int, list[dict[str, str]]]:
    pages: dict[int, list[dict[str, str]]] = {page: [] for page in range(1, 10)}
    with Path(mapping_path).open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            pages[int(row["template_page"])].append(row)
    for page in pages:
        pages[page].sort(key=lambda row: int(row["cell_index"]))
    return pages


def _fit_font(character: str, max_width: int, max_height: int, font_path: Path) -> ImageFont.FreeTypeFont:
    size = max(12, int(max_height * 0.80))
    while size > 10:
        font = ImageFont.truetype(str(font_path), size=size)
        bbox = font.getbbox(character or "?")
        width = max(1, bbox[2] - bbox[0])
        height = max(1, bbox[3] - bbox[1])
        if width <= max_width * 0.88 and height <= max_height * 0.86:
            return font
        size -= 2
    return ImageFont.truetype(str(FALLBACK_FONT), size=12)


def render_written_page(
    page: int,
    *,
    dpi: int = 150,
    seed: int = 20260728,
    blank_dir: Path | str = DEFAULT_BLANK_DIR,
    mapping_path: Path | str = DEFAULT_MAPPING_PATH,
    missing_cells: set[str] | None = None,
) -> np.ndarray:
    width, height = canonical_size(dpi)
    blank = cv2.imread(str(Path(blank_dir) / f"template-page-{page:02d}.png"), cv2.IMREAD_COLOR)
    if blank is None:
        raise FileNotFoundError(f"빈 템플릿 페이지가 없습니다: {page}")
    blank = cv2.resize(blank, (width, height), interpolation=cv2.INTER_AREA)
    rgb = cv2.cvtColor(blank, cv2.COLOR_BGR2RGB)
    image = Image.fromarray(rgb)
    layout = load_layout(DEFAULT_LAYOUT_PATH)
    cells = load_cells(layout)
    rows = _mapping_by_page(mapping_path)[page]
    rng = random.Random(seed + page * 1000)
    for cell, row in zip(cells, rows, strict=False):
        cell_id = row["cell_id"]
        if missing_cells and cell_id in missing_cells:
            continue
        character = row["character"] or "•"
        x, y, cell_width, cell_height = normalized_box_to_pixels(cell.box_norm, width, height)
        left, top, right, bottom = relative_roi_to_pixels(cell.writing_roi_norm, cell_width, cell_height)
        roi_width = right - left
        roi_height = bottom - top
        font = _fit_font(character, roi_width, roi_height, DEFAULT_FONT)
        layer = Image.new("RGBA", (roi_width, roi_height), (255, 255, 255, 0))
        draw = ImageDraw.Draw(layer)
        bbox = draw.textbbox((0, 0), character, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        px = (roi_width - text_width) / 2 - bbox[0] + rng.uniform(-roi_width * 0.035, roi_width * 0.035)
        py = (roi_height - text_height) / 2 - bbox[1] + rng.uniform(-roi_height * 0.035, roi_height * 0.035)
        tone = rng.randint(10, 38)
        draw.text((px, py), character, font=font, fill=(tone, tone, tone, 255), stroke_width=0)
        angle = rng.uniform(-2.2, 2.2)
        layer = layer.rotate(angle, resample=Image.Resampling.BICUBIC, expand=False)
        image.alpha_composite(layer, dest=(x + left, y + top)) if image.mode == "RGBA" else image.paste(layer, (x + left, y + top), layer)
    return cv2.cvtColor(np.asarray(image.convert("RGB")), cv2.COLOR_RGB2BGR)


def synthesize_capture(
    page_image: np.ndarray,
    *,
    seed: int,
    perspective: float = 0.065,
    brightness: float = -4.0,
    contrast: float = 1.02,
    blur: int = 1,
    noise: float = 2.5,
    jpeg_quality: int = 86,
    shadow: float = 0.12,
) -> tuple[np.ndarray, np.ndarray]:
    rng = random.Random(seed)
    src_h, src_w = page_image.shape[:2]
    canvas_w = int(src_w * 1.24)
    canvas_h = int(src_h * 1.18)
    margin_x = int(canvas_w * 0.10)
    margin_y = int(canvas_h * 0.075)
    base = np.array([
        [margin_x, margin_y], [canvas_w - margin_x, margin_y],
        [canvas_w - margin_x, canvas_h - margin_y], [margin_x, canvas_h - margin_y],
    ], dtype=np.float32)
    amount_x = perspective * canvas_w
    amount_y = perspective * canvas_h
    destination = base + np.array([
        [rng.uniform(-amount_x, amount_x), rng.uniform(-amount_y, amount_y)] for _ in range(4)
    ], dtype=np.float32)
    source = np.array([[0, 0], [src_w - 1, 0], [src_w - 1, src_h - 1], [0, src_h - 1]], dtype=np.float32)
    matrix = cv2.getPerspectiveTransform(source, destination)
    canvas = cv2.warpPerspective(page_image, matrix, (canvas_w, canvas_h), borderValue=(246, 246, 246))
    image = canvas.astype(np.float32)
    if shadow > 0:
        yy, xx = np.mgrid[0:canvas_h, 0:canvas_w]
        angle = rng.uniform(0, math.tau)
        direction = np.cos(angle) * (xx / max(1, canvas_w - 1) - 0.5) + np.sin(angle) * (yy / max(1, canvas_h - 1) - 0.5)
        image *= (1.0 - shadow * (direction + 0.5))[..., None]
    image = (image - 127.5) * contrast + 127.5 + brightness
    if noise > 0:
        image += np.random.default_rng(seed).normal(0.0, noise, image.shape).astype(np.float32)
    image = np.clip(image, 0, 255).astype(np.uint8)
    if blur >= 3:
        image = cv2.GaussianBlur(image, (blur, blur), 0)
    if jpeg_quality < 100:
        ok, encoded = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, jpeg_quality])
        if ok:
            image = cv2.imdecode(encoded, cv2.IMREAD_COLOR)
    layout = load_layout(DEFAULT_LAYOUT_PATH)
    canonical_markers = destination_markers(layout, src_w, src_h).reshape(-1, 1, 2)
    marker_points = cv2.perspectiveTransform(canonical_markers, matrix).reshape(-1, 2)
    return image, marker_points


def generate_benchmark_session(output_dir: Path | str, *, seed: int = 20260728, dpi: int = 150) -> dict:
    output = Path(output_dir)
    photos = output / "photos"
    photos.mkdir(parents=True, exist_ok=True)
    manual: dict[str, list[list[float]]] = {}
    records: list[dict] = []
    order = [4, 1, 8, 3, 7, 2, 9, 6, 5]
    for sequence, page in enumerate(order, start=1):
        written = render_written_page(page, dpi=dpi, seed=seed)
        image, markers = synthesize_capture(
            written,
            seed=seed + page * 100,
            perspective=0.04 + (page % 4) * 0.012,
            brightness=-8 + page,
            contrast=0.96 + (page % 3) * 0.04,
            blur=3 if page in {4, 9} else 1,
            noise=2.0 + page * 0.25,
            jpeg_quality=82 - (page % 3) * 6,
            shadow=0.08 + (page % 4) * 0.04,
        )
        name = f"capture-{sequence:02d}-unknown.jpg"
        if page == 7:
            center = tuple(np.round(markers[0]).astype(int))
            radius = max(28, int(min(image.shape[:2]) * 0.025))
            cv2.rectangle(image, (center[0] - radius, center[1] - radius), (center[0] + radius, center[1] + radius), (246, 246, 246), -1)
            manual[name] = markers.round(3).tolist()
        cv2.imwrite(str(photos / name), image)
        records.append({"file": name, "page": page, "manual": page == 7})
    # Page 3 duplicate with intentionally poor quality.
    written = render_written_page(3, dpi=dpi, seed=seed + 333)
    duplicate, _ = synthesize_capture(written, seed=seed + 3333, perspective=0.08, brightness=-24, contrast=1.12, blur=7, noise=8.0, jpeg_quality=55, shadow=0.28)
    duplicate_name = "capture-10-duplicate.jpg"
    cv2.imwrite(str(photos / duplicate_name), duplicate)
    records.append({"file": duplicate_name, "page": 3, "manual": False, "duplicate": True})
    manual_path = output / "manual-corners.json"
    manual_path.write_text(json.dumps({"files": manual}, ensure_ascii=False, indent=2), encoding="utf-8")
    ground_truth = {"schema_version": "1.8.0", "seed": seed, "dpi": dpi, "records": records}
    (output / "ground-truth.json").write_text(json.dumps(ground_truth, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"photos": photos, "manual_corners": manual_path, "ground_truth": ground_truth}
