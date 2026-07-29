from __future__ import annotations

import io

import cairosvg
import cv2
import numpy as np

from .errors import VectorizationError


def rasterize_svg(svg: str, width: int, height: int) -> np.ndarray:
    try:
        png = cairosvg.svg2png(bytestring=svg.encode("utf-8"), output_width=width, output_height=height)
    except Exception as error:  # cairo boundary
        raise VectorizationError(f"SVG 래스터화에 실패했습니다: {error}") from error
    data = np.frombuffer(png, dtype=np.uint8)
    image = cv2.imdecode(data, cv2.IMREAD_UNCHANGED)
    if image is None:
        raise VectorizationError("SVG 래스터 결과를 읽지 못했습니다.")
    if image.ndim == 3 and image.shape[2] == 4:
        alpha = image[:, :, 3]
        rgb = image[:, :, :3]
        gray = cv2.cvtColor(rgb, cv2.COLOR_BGR2GRAY)
        # Cairo often emits transparent background. Composite onto white.
        gray = (gray.astype(np.float32) * (alpha.astype(np.float32) / 255.0) + 255.0 * (1.0 - alpha.astype(np.float32) / 255.0)).astype(np.uint8)
    elif image.ndim == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image
    return np.where(gray < 128, 255, 0).astype(np.uint8)


def mask_iou(reference: np.ndarray, candidate: np.ndarray) -> float:
    ref = reference > 0
    cand = candidate > 0
    union = int(np.count_nonzero(ref | cand))
    if union == 0:
        return 1.0
    intersection = int(np.count_nonzero(ref & cand))
    return intersection / float(union)


def difference_image(reference: np.ndarray, candidate: np.ndarray) -> np.ndarray:
    canvas = np.full((reference.shape[0], reference.shape[1], 3), 255, dtype=np.uint8)
    ref = reference > 0
    cand = candidate > 0
    canvas[ref & cand] = (32, 32, 32)
    canvas[ref & ~cand] = (40, 80, 220)   # missing from vector
    canvas[~ref & cand] = (220, 120, 30)  # added by vector
    return canvas


def overlay_image(reference: np.ndarray, candidate: np.ndarray) -> np.ndarray:
    canvas = np.full((reference.shape[0], reference.shape[1], 3), 255, dtype=np.uint8)
    canvas[reference > 0] = (185, 185, 185)
    canvas[candidate > 0] = (30, 30, 30)
    return canvas
