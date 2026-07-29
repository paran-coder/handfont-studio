from __future__ import annotations

from typing import Iterable

import cv2
import numpy as np

from .models import CellLayout


def normalized_box_to_pixels(box: Iterable[float], width: int, height: int) -> tuple[int, int, int, int]:
    x, y, w, h = box
    return (
        int(round(x * width)),
        int(round(y * height)),
        int(round(w * width)),
        int(round(h * height)),
    )


def relative_roi_to_pixels(roi: Iterable[float], cell_width: int, cell_height: int) -> tuple[int, int, int, int]:
    x1, y1, x2, y2 = roi
    left = int(round(x1 * cell_width))
    top = int(round(y1 * cell_height))
    right = int(round(x2 * cell_width))
    bottom = int(round(y2 * cell_height))
    return left, top, right, bottom


def extract_cells(rectified: np.ndarray, cells: list[CellLayout]) -> list[dict]:
    height, width = rectified.shape[:2]
    output: list[dict] = []
    for cell in cells:
        x, y, w, h = normalized_box_to_pixels(cell.box_norm, width, height)
        x = max(0, min(x, width - 1))
        y = max(0, min(y, height - 1))
        w = max(1, min(w, width - x))
        h = max(1, min(h, height - y))
        crop = rectified[y : y + h, x : x + w]
        left, top, right, bottom = relative_roi_to_pixels(cell.writing_roi_norm, w, h)
        left = max(0, min(left, w - 1))
        top = max(0, min(top, h - 1))
        right = max(left + 1, min(right, w))
        bottom = max(top + 1, min(bottom, h))
        writing = crop[top:bottom, left:right]
        output.append(
            {
                "layout": cell,
                "box_px": [x, y, w, h],
                "writing_roi_px": [left, top, right, bottom],
                "cell": crop,
                "writing": writing,
            }
        )
    return output


def draw_overlay(rectified: np.ndarray, extracted: list[dict], statuses: dict[str, str] | None = None) -> np.ndarray:
    overlay = rectified.copy()
    height, width = overlay.shape[:2]
    for item in extracted:
        x, y, w, h = item["box_px"]
        cell_id = item.get("cell_id", item["layout"].cell_id)
        status = (statuses or {}).get(cell_id, "unknown")
        thickness = max(2, int(round(width / 900)))
        if status == "ok":
            color = (40, 120, 40)
        elif status == "too_dense":
            color = (40, 40, 180)
        elif status in {"missing", "too_sparse"}:
            color = (0, 130, 210)
        else:
            color = (140, 90, 20)
        cv2.rectangle(overlay, (x, y), (x + w, y + h), color, thickness)
        font_scale = max(0.30, min(0.60, width / 4500.0))
        text_y = max(18, y - max(4, int(round(height / 900))))
        cv2.putText(
            overlay,
            cell_id,
            (x + 4, text_y),
            cv2.FONT_HERSHEY_SIMPLEX,
            font_scale,
            color,
            max(1, thickness - 1),
            cv2.LINE_AA,
        )
    return overlay
