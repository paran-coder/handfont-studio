from __future__ import annotations

import cv2
import numpy as np

from .errors import EmptyMaskError, InputMaskError
from .models import VectorizeOptions


def _to_gray(image: np.ndarray) -> np.ndarray:
    if image.ndim == 2:
        return image.copy()
    if image.ndim == 3 and image.shape[2] == 4:
        alpha = image[:, :, 3].astype(np.float32) / 255.0
        rgb = image[:, :, :3].astype(np.float32)
        composited = rgb * alpha[..., None] + 255.0 * (1.0 - alpha[..., None])
        return cv2.cvtColor(composited.astype(np.uint8), cv2.COLOR_BGR2GRAY)
    if image.ndim == 3 and image.shape[2] == 3:
        return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    raise InputMaskError("마스크는 회색조, BGR 또는 BGRA 이미지여야 합니다.")


def _border_pixels(gray: np.ndarray) -> np.ndarray:
    thickness = max(1, int(round(min(gray.shape[:2]) * 0.025)))
    return np.concatenate(
        [
            gray[:thickness, :].ravel(),
            gray[-thickness:, :].ravel(),
            gray[:, :thickness].ravel(),
            gray[:, -thickness:].ravel(),
        ]
    )


def _remove_small_components(mask: np.ndarray, minimum_area: int) -> np.ndarray:
    count, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    cleaned = np.zeros_like(mask)
    for index in range(1, count):
        if int(stats[index, cv2.CC_STAT_AREA]) >= minimum_area:
            cleaned[labels == index] = 255
    return cleaned


def normalize_mask(image: np.ndarray, options: VectorizeOptions) -> tuple[np.ndarray, dict]:
    gray = _to_gray(image)
    if min(gray.shape[:2]) < 16:
        raise InputMaskError("마스크 해상도가 너무 작습니다. 최소 한 변이 16px 이상이어야 합니다.")

    blur = cv2.GaussianBlur(gray, (3, 3), 0)
    border_median = float(np.median(_border_pixels(blur)))
    if options.threshold is None:
        threshold_value, binary = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    else:
        threshold_value = float(options.threshold)
        _, binary = cv2.threshold(blur, int(options.threshold), 255, cv2.THRESH_BINARY)

    # The page pipeline emits white ink on a black background, while user-provided
    # masks are frequently black ink on white. Infer the background from the border.
    foreground_is_bright = border_median < 127.5
    mask = binary if foreground_is_bright else cv2.bitwise_not(binary)

    if options.close_kernel > 1:
        kernel_size = options.close_kernel if options.close_kernel % 2 == 1 else options.close_kernel + 1
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    mask = _remove_small_components(mask, max(1, options.minimum_component_area))

    foreground_pixels = int(np.count_nonzero(mask))
    foreground_ratio = foreground_pixels / float(mask.size)
    if foreground_ratio < options.minimum_foreground_ratio:
        raise EmptyMaskError(
            f"전경이 너무 적어 윤곽선을 만들 수 없습니다: {foreground_ratio:.6f}"
        )
    if foreground_ratio > options.maximum_foreground_ratio:
        raise InputMaskError(
            f"전경이 지나치게 많아 배경/전경이 뒤바뀌었을 가능성이 큽니다: {foreground_ratio:.6f}"
        )

    points = cv2.findNonZero(mask)
    if points is None:
        raise InputMaskError("전경 픽셀이 없습니다.")
    x, y, width, height = cv2.boundingRect(points)
    return mask, {
        "threshold": round(threshold_value, 3),
        "border_median": round(border_median, 3),
        "foreground_is_bright": foreground_is_bright,
        "foreground_pixels": foreground_pixels,
        "foreground_ratio": round(foreground_ratio, 7),
        "bbox": [int(x), int(y), int(width), int(height)],
        "size": [int(mask.shape[1]), int(mask.shape[0])],
    }
