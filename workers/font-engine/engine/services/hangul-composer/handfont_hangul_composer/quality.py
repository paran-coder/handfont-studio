from __future__ import annotations

import cv2
import numpy as np


def foreground_bbox(mask: np.ndarray) -> tuple[int, int, int, int] | None:
    ys, xs = np.where(mask > 0)
    if len(xs) == 0:
        return None
    return int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1


def normalize_foreground(mask: np.ndarray, canvas: int = 480, body: int = 400) -> np.ndarray:
    bbox = foreground_bbox(mask)
    if bbox is None:
        return np.zeros((canvas, canvas), dtype=np.uint8)
    x0, y0, x1, y1 = bbox
    crop = mask[y0:y1, x0:x1]
    height, width = crop.shape
    scale = min(body / max(width, 1), body / max(height, 1))
    new_width = max(1, int(round(width * scale)))
    new_height = max(1, int(round(height * scale)))
    resized = cv2.resize(
        crop,
        (new_width, new_height),
        interpolation=cv2.INTER_AREA if scale < 1 else cv2.INTER_CUBIC,
    )
    resized = (resized > 96).astype(np.uint8) * 255
    output = np.zeros((canvas, canvas), dtype=np.uint8)
    x = (canvas - new_width) // 2
    y = (canvas - new_height) // 2
    output[y : y + new_height, x : x + new_width] = resized
    return output


def aligned_iou(generated: np.ndarray, reference: np.ndarray, max_shift: int = 10) -> tuple[float, tuple[int, int]]:
    left = normalize_foreground(generated) > 0
    right = normalize_foreground(reference) > 0
    height, width = left.shape
    left_total = int(left.sum())
    right_total = int(right.sum())
    best = -1.0
    best_shift = (0, 0)
    for dy in range(-max_shift, max_shift + 1, 2):
        left_y0 = max(0, dy)
        right_y0 = max(0, -dy)
        overlap_height = height - abs(dy)
        if overlap_height <= 0:
            continue
        for dx in range(-max_shift, max_shift + 1, 2):
            left_x0 = max(0, dx)
            right_x0 = max(0, -dx)
            overlap_width = width - abs(dx)
            if overlap_width <= 0:
                continue
            left_view = left[left_y0:left_y0 + overlap_height, left_x0:left_x0 + overlap_width]
            right_view = right[right_y0:right_y0 + overlap_height, right_x0:right_x0 + overlap_width]
            intersection = int(np.logical_and(left_view, right_view).sum())
            union = left_total + right_total - intersection
            score = intersection / max(union, 1)
            if score > best:
                best = score
                best_shift = (dx, dy)
    return best, best_shift


def symmetric_chamfer(generated: np.ndarray, reference: np.ndarray) -> float:
    left = normalize_foreground(generated) > 0
    right = normalize_foreground(reference) > 0
    left_edge = cv2.morphologyEx(left.astype(np.uint8), cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8)) > 0
    right_edge = cv2.morphologyEx(right.astype(np.uint8), cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8)) > 0
    if not left_edge.any() or not right_edge.any():
        return 1.0
    distance_to_right = cv2.distanceTransform((~right_edge).astype(np.uint8), cv2.DIST_L2, 3)
    distance_to_left = cv2.distanceTransform((~left_edge).astype(np.uint8), cv2.DIST_L2, 3)
    distance = (float(distance_to_right[left_edge].mean()) + float(distance_to_left[right_edge].mean())) / 2.0
    return min(1.0, distance / 24.0)


def pair_overlap_ratio(layers: list[np.ndarray]) -> float:
    maximum = 0.0
    for index, left in enumerate(layers):
        left_pixels = int(np.count_nonzero(left))
        for right in layers[index + 1 :]:
            right_pixels = int(np.count_nonzero(right))
            intersection = int(np.logical_and(left > 0, right > 0).sum())
            maximum = max(maximum, intersection / max(1, min(left_pixels, right_pixels)))
    return maximum


def evaluate(generated: np.ndarray, layers: list[np.ndarray], reference: np.ndarray) -> dict:
    generated_pixels = int(np.count_nonzero(generated))
    reference_pixels = int(np.count_nonzero(reference))
    iou, shift = aligned_iou(generated, reference)
    chamfer = symmetric_chamfer(generated, reference)
    density_ratio = generated_pixels / max(reference_pixels, 1)
    density_error = abs(np.log(max(density_ratio, 1e-6)))
    overlap = pair_overlap_ratio(layers)
    bbox = foreground_bbox(generated)
    overflow = 0
    if bbox is not None:
        x0, y0, x1, y1 = bbox
        overflow = int(x0 < 15 or y0 < 15 or x1 > generated.shape[1] - 15 or y1 > generated.shape[0] - 15)
    quality_score = 100.0 * (
        0.62 * iou
        + 0.20 * (1.0 - chamfer)
        + 0.10 * max(0.0, 1.0 - min(density_error, 1.0))
        + 0.08 * max(0.0, 1.0 - min(overlap / 0.35, 1.0))
    )
    return {
        "aligned_iou": round(iou, 6),
        "best_shift": list(shift),
        "normalized_chamfer": round(chamfer, 6),
        "density_ratio": round(density_ratio, 6),
        "density_log_error": round(float(density_error), 6),
        "max_pair_overlap_ratio": round(overlap, 6),
        "overflow": bool(overflow),
        "generated_ink_pixels": generated_pixels,
        "reference_ink_pixels": reference_pixels,
        "quality_score": round(quality_score, 4),
        "status": "ok" if quality_score >= 55 and iou >= 0.35 and not overflow else "review",
    }
