from __future__ import annotations

import cv2
import numpy as np


def canonical_size(output_dpi: int) -> tuple[int, int]:
    width = int(round(210.0 / 25.4 * output_dpi))
    height = int(round(297.0 / 25.4 * output_dpi))
    return width, height


def destination_markers(layout: dict, width: int, height: int) -> np.ndarray:
    return np.array(
        [[x * width, y * height] for x, y in layout["marker_centers_norm"]],
        dtype=np.float32,
    )


def rectify_page(image: np.ndarray, source_points: np.ndarray, layout: dict, output_dpi: int = 300) -> tuple[np.ndarray, np.ndarray]:
    width, height = canonical_size(output_dpi)
    destination = destination_markers(layout, width, height)
    transform = cv2.getPerspectiveTransform(source_points.astype(np.float32), destination)
    rectified = cv2.warpPerspective(
        image,
        transform,
        (width, height),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(255, 255, 255),
    )
    return rectified, transform
