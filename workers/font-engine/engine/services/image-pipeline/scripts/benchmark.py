from __future__ import annotations

import argparse
import json
import math
import random
import statistics
import sys
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from handfont_pipeline.cells import normalized_box_to_pixels, relative_roi_to_pixels
from handfont_pipeline.config import DEFAULT_BLANK_DIR, DEFAULT_LAYOUT_PATH, load_cells, load_layout
from handfont_pipeline.markers import detect_markers
from handfont_pipeline.perspective import canonical_size, rectify_page


@dataclass(frozen=True)
class Scenario:
    name: str
    perspective: float
    brightness: float
    contrast: float
    blur: int
    noise: float
    jpeg_quality: int
    shadow: float


SCENARIOS = [
    Scenario("clean", 0.010, 0.0, 1.0, 0, 0.0, 100, 0.0),
    Scenario("mild-perspective", 0.035, -4.0, 1.0, 0, 1.0, 95, 0.04),
    Scenario("rotation-brightness", 0.055, 14.0, 0.92, 1, 1.5, 92, 0.08),
    Scenario("shadow-blur", 0.065, -10.0, 1.08, 3, 2.0, 90, 0.22),
    Scenario("jpeg-noise", 0.075, 5.0, 0.95, 1, 5.0, 72, 0.10),
    Scenario("combined", 0.090, -12.0, 1.10, 3, 6.0, 68, 0.28),
]


def add_synthetic_ink(page: np.ndarray, layout: dict, seed: int) -> np.ndarray:
    result = page.copy()
    rng = random.Random(seed)
    height, width = result.shape[:2]
    cells = load_cells(layout)
    for cell in cells[:8]:
        x, y, w, h = normalized_box_to_pixels(cell.box_norm, width, height)
        left, top, right, bottom = relative_roi_to_pixels(cell.writing_roi_norm, w, h)
        rx1, ry1 = x + left, y + top
        rx2, ry2 = x + right, y + bottom
        points = []
        count = rng.randint(4, 7)
        for index in range(count):
            px = int(rx1 + (rx2 - rx1) * (0.15 + 0.7 * index / max(1, count - 1)))
            py = rng.randint(int(ry1 + (ry2 - ry1) * 0.15), int(ry2 - (ry2 - ry1) * 0.15))
            points.append([px, py])
        cv2.polylines(
            result,
            [np.asarray(points, dtype=np.int32)],
            False,
            (15, 15, 15),
            max(3, int(round(width / 620))),
            cv2.LINE_AA,
        )
        if rng.random() > 0.35:
            center = (rng.randint(rx1 + 20, rx2 - 20), rng.randint(ry1 + 20, ry2 - 20))
            axes = (rng.randint(18, 45), rng.randint(22, 55))
            cv2.ellipse(result, center, axes, rng.randint(-30, 30), 0, 300, (20, 20, 20), max(3, int(round(width / 700))), cv2.LINE_AA)
    return result


def transform_points(points: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    points = points.reshape(-1, 1, 2).astype(np.float32)
    return cv2.perspectiveTransform(points, matrix).reshape(-1, 2)


def synthesize(page: np.ndarray, scenario: Scenario, seed: int) -> tuple[np.ndarray, np.ndarray]:
    rng = random.Random(seed)
    src_h, src_w = page.shape[:2]
    canvas_w = int(src_w * 1.22)
    canvas_h = int(src_h * 1.18)
    margin_x = int(canvas_w * 0.10)
    margin_y = int(canvas_h * 0.075)
    base = np.array(
        [
            [margin_x, margin_y],
            [canvas_w - margin_x, margin_y],
            [canvas_w - margin_x, canvas_h - margin_y],
            [margin_x, canvas_h - margin_y],
        ],
        dtype=np.float32,
    )
    amount_x = scenario.perspective * canvas_w
    amount_y = scenario.perspective * canvas_h
    jitter = np.array(
        [[rng.uniform(-amount_x, amount_x), rng.uniform(-amount_y, amount_y)] for _ in range(4)],
        dtype=np.float32,
    )
    destination = base + jitter
    source = np.array([[0, 0], [src_w - 1, 0], [src_w - 1, src_h - 1], [0, src_h - 1]], dtype=np.float32)
    page_to_canvas = cv2.getPerspectiveTransform(source, destination)
    canvas = cv2.warpPerspective(page, page_to_canvas, (canvas_w, canvas_h), borderValue=(247, 247, 247))

    image = canvas.astype(np.float32)
    if scenario.shadow > 0:
        yy, xx = np.mgrid[0:canvas_h, 0:canvas_w]
        angle = rng.uniform(0, math.tau)
        direction = (np.cos(angle) * (xx / max(1, canvas_w - 1) - 0.5) + np.sin(angle) * (yy / max(1, canvas_h - 1) - 0.5))
        factor = 1.0 - scenario.shadow * (direction + 0.5)
        image *= factor[..., None]
    image = (image - 127.5) * scenario.contrast + 127.5 + scenario.brightness
    if scenario.noise > 0:
        noise = np.random.default_rng(seed).normal(0.0, scenario.noise, image.shape).astype(np.float32)
        image += noise
    image = np.clip(image, 0, 255).astype(np.uint8)
    if scenario.blur >= 3:
        image = cv2.GaussianBlur(image, (scenario.blur, scenario.blur), 0)
    if scenario.jpeg_quality < 100:
        ok, encoded = cv2.imencode('.jpg', image, [cv2.IMWRITE_JPEG_QUALITY, scenario.jpeg_quality])
        if ok:
            image = cv2.imdecode(encoded, cv2.IMREAD_COLOR)
    return image, page_to_canvas


def cell_corner_points(layout: dict, width: int, height: int) -> np.ndarray:
    points = []
    for cell in load_cells(layout):
        x, y, w, h = normalized_box_to_pixels(cell.box_norm, width, height)
        points.extend([[x, y], [x + w, y], [x + w, y + h], [x, y + h]])
    return np.asarray(points, dtype=np.float32)


def run(output: Path, dpi: int, seed: int) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    layout = load_layout(DEFAULT_LAYOUT_PATH)
    canonical_w, canonical_h = canonical_size(dpi)
    canonical_points = cell_corner_points(layout, canonical_w, canonical_h)
    marker_norm = np.asarray(layout['marker_centers_norm'], dtype=np.float32)
    canonical_markers = marker_norm * np.array([canonical_w, canonical_h], dtype=np.float32)
    records = []

    for page_number in range(1, 10):
        blank_path = DEFAULT_BLANK_DIR / f'template-page-{page_number:02d}.png'
        page = cv2.imread(str(blank_path), cv2.IMREAD_COLOR)
        if page is None:
            raise RuntimeError(f'blank page missing: {blank_path}')
        page = cv2.resize(page, (canonical_w, canonical_h), interpolation=cv2.INTER_AREA)
        page = add_synthetic_ink(page, layout, seed + page_number * 100)

        for scenario_index, scenario in enumerate(SCENARIOS):
            case_seed = seed + page_number * 1000 + scenario_index
            synthetic, page_to_canvas = synthesize(page, scenario, case_seed)
            record = {'page': page_number, 'scenario': scenario.name, 'success': False}
            try:
                detected = detect_markers(synthetic)
                gt_markers = transform_points(canonical_markers, page_to_canvas)
                marker_error = np.linalg.norm(detected.points - gt_markers, axis=1)
                _, estimated = rectify_page(synthetic, detected.points, layout, dpi)
                synthetic_cell_points = transform_points(canonical_points, page_to_canvas)
                recovered = transform_points(synthetic_cell_points, estimated)
                cell_error = np.linalg.norm(recovered - canonical_points, axis=1)
                record.update(
                    {
                        'success': True,
                        'confidence': detected.confidence,
                        'marker_mean_error_px': float(np.mean(marker_error)),
                        'marker_max_error_px': float(np.max(marker_error)),
                        'cell_corner_rmse_px': float(np.sqrt(np.mean(np.square(cell_error)))),
                        'input_size': [synthetic.shape[1], synthetic.shape[0]],
                    }
                )
                if page_number == 1 and scenario.name in {'clean', 'combined'}:
                    cv2.imwrite(str(output / f'sample-{scenario.name}.jpg'), synthetic)
                    rectified, _ = rectify_page(synthetic, detected.points, layout, dpi)
                    cv2.imwrite(str(output / f'sample-{scenario.name}-rectified.png'), rectified)
            except Exception as error:
                record['error'] = str(error)
            records.append(record)

    successes = [item for item in records if item['success']]
    failures = [item for item in records if not item['success']]
    summary = {
        'schema_version': '1.3.0',
        'dpi': dpi,
        'seed': seed,
        'total_cases': len(records),
        'successful_cases': len(successes),
        'failed_cases': len(failures),
        'success_rate': len(successes) / len(records),
        'mean_marker_error_px': statistics.fmean(item['marker_mean_error_px'] for item in successes) if successes else None,
        'p95_marker_error_px': float(np.percentile([item['marker_mean_error_px'] for item in successes], 95)) if successes else None,
        'max_marker_error_px': max((item['marker_max_error_px'] for item in successes), default=None),
        'mean_cell_corner_rmse_px': statistics.fmean(item['cell_corner_rmse_px'] for item in successes) if successes else None,
        'p95_cell_corner_rmse_px': float(np.percentile([item['cell_corner_rmse_px'] for item in successes], 95)) if successes else None,
        'failures': failures,
    }
    payload = {'summary': summary, 'records': records}
    (output / 'benchmark-results.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--dpi', type=int, default=150)
    parser.add_argument('--seed', type=int, default=20260728)
    args = parser.parse_args()
    run(args.output, args.dpi, args.seed)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
