from __future__ import annotations

import cv2
import numpy as np


def capture_quality(image: np.ndarray, marker_confidence: float, page_confidence: float, marker_method: str) -> tuple[float, float, float, list[str]]:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    laplacian_variance = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    sharpness = min(1.0, laplacian_variance / 650.0)
    clipped_dark = float(np.mean(gray < 8))
    clipped_light = float(np.mean(gray > 250))
    mean = float(np.mean(gray))
    mean_penalty = min(1.0, abs(mean - 205.0) / 130.0)
    exposure = max(0.0, 1.0 - 2.5 * (clipped_dark + clipped_light) - 0.25 * mean_penalty)
    marker_factor = marker_confidence if marker_method == "automatic" else 0.82
    score = 0.42 * marker_factor + 0.30 * page_confidence + 0.18 * sharpness + 0.10 * exposure
    warnings: list[str] = []
    if sharpness < 0.25:
        warnings.append("blur")
    if exposure < 0.55:
        warnings.append("exposure")
    if marker_method != "automatic":
        warnings.append("manual-corners")
    if page_confidence < 0.45:
        warnings.append("page-id-low-confidence")
    return sharpness, exposure, float(max(0.0, min(1.0, score))), warnings
