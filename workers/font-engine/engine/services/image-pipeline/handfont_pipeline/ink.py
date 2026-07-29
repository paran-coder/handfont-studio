from __future__ import annotations

import cv2
import numpy as np


def _gray(image: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image.copy()


def _flat_field(gray: np.ndarray) -> np.ndarray:
    source = gray.astype(np.float32)
    sigma = max(8.0, min(gray.shape[:2]) / 5.0)
    background = cv2.GaussianBlur(source, (0, 0), sigmaX=sigma, sigmaY=sigma)
    normalized = source * 245.0 / np.maximum(background, 32.0)
    white_point = float(np.percentile(normalized, 96))
    if white_point > 1.0:
        normalized *= 255.0 / white_point
    return np.clip(normalized, 0, 255).astype(np.uint8)


def _photometric_match(input_gray: np.ndarray, blank_gray: np.ndarray) -> np.ndarray:
    source = _flat_field(input_gray)
    target = _flat_field(blank_gray)
    source_white = float(np.percentile(source, 96))
    target_white = float(np.percentile(target, 96))
    scale = target_white / max(source_white, 1.0)
    scale = float(np.clip(scale, 0.85, 1.18))
    return np.clip(source.astype(np.float32) * scale, 0, 255).astype(np.uint8)


def _remove_small_components(mask: np.ndarray, minimum_area: int) -> np.ndarray:
    count, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    cleaned = np.zeros_like(mask)
    for index in range(1, count):
        if int(stats[index, cv2.CC_STAT_AREA]) >= minimum_area:
            cleaned[labels == index] = 255
    return cleaned


def extract_ink_mask(writing: np.ndarray, blank_writing: np.ndarray, minimum_area: int = 18) -> tuple[np.ndarray, dict]:
    if writing.shape[:2] != blank_writing.shape[:2]:
        blank_writing = cv2.resize(blank_writing, (writing.shape[1], writing.shape[0]), interpolation=cv2.INTER_AREA)

    input_gray = _photometric_match(_gray(writing), _gray(blank_writing))
    blank_gray = _flat_field(_gray(blank_writing))

    input_blur = cv2.GaussianBlur(input_gray, (3, 3), 0)
    blank_blur = cv2.GaussianBlur(blank_gray, (3, 3), 0)
    difference = blank_blur.astype(np.int16) - input_blur.astype(np.int16)

    # Added ink is darker than the blank template. A second dark-pixel condition
    # prevents broad illumination changes from becoming foreground.
    difference_mask = (difference > 18).astype(np.uint8) * 255
    dark_mask = (input_gray < 205).astype(np.uint8) * 255
    mask = cv2.bitwise_and(difference_mask, dark_mask)

    # Ignore the cell boundary area and repair small interruptions caused by guide lines.
    margin_x = max(2, int(round(mask.shape[1] * 0.015)))
    margin_y = max(2, int(round(mask.shape[0] * 0.015)))
    mask[:margin_y, :] = 0
    mask[-margin_y:, :] = 0
    mask[:, :margin_x] = 0
    mask[:, -margin_x:] = 0
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8), iterations=1)
    mask = _remove_small_components(mask, minimum_area)

    nonzero = cv2.findNonZero(mask)
    if nonzero is None:
        bbox = None
        ink_ratio = 0.0
    else:
        x, y, w, h = cv2.boundingRect(nonzero)
        bbox = [int(x), int(y), int(w), int(h)]
        ink_ratio = float(np.count_nonzero(mask)) / float(mask.size)

    if ink_ratio < 0.0012:
        status = "missing"
    elif ink_ratio < 0.006:
        status = "too_sparse"
    elif ink_ratio > 0.33:
        status = "too_dense"
    else:
        status = "ok"

    return mask, {
        "ink_ratio": round(ink_ratio, 6),
        "ink_bbox": bbox,
        "status": status,
        "foreground_pixels": int(np.count_nonzero(mask)),
    }


def render_ink(mask: np.ndarray) -> np.ndarray:
    canvas = np.full((mask.shape[0], mask.shape[1], 3), 255, dtype=np.uint8)
    canvas[mask > 0] = (0, 0, 0)
    return canvas
