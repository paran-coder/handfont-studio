from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping

import cv2
import numpy as np

from .compat import IMAGE_PIPELINE_ROOT  # noqa: F401
from handfont_pipeline.markers import order_points


def load_manual_corners(path: Path | str | None) -> dict[str, np.ndarray]:
    if path is None:
        return {}
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    entries = payload.get("files", payload)
    if not isinstance(entries, Mapping):
        raise ValueError("수동 모서리 JSON은 파일명→4개 좌표 매핑이어야 합니다.")
    result: dict[str, np.ndarray] = {}
    for name, value in entries.items():
        points = np.asarray(value, dtype=np.float32)
        if points.shape != (4, 2):
            raise ValueError(f"{name}: 수동 모서리는 4x2 좌표여야 합니다.")
        result[str(name)] = order_points(points)
    return result


def validate_manual_corners(points: np.ndarray, image_width: int, image_height: int) -> np.ndarray:
    ordered = order_points(np.asarray(points, dtype=np.float32))
    if ordered.shape != (4, 2) or not np.isfinite(ordered).all():
        raise ValueError("수동 모서리 좌표가 유효하지 않습니다.")
    if np.any(ordered[:, 0] < 0) or np.any(ordered[:, 0] >= image_width):
        raise ValueError("수동 모서리 X 좌표가 이미지 범위를 벗어났습니다.")
    if np.any(ordered[:, 1] < 0) or np.any(ordered[:, 1] >= image_height):
        raise ValueError("수동 모서리 Y 좌표가 이미지 범위를 벗어났습니다.")
    area = abs(float(cv2.contourArea(ordered.reshape(-1, 1, 2))))
    if area < image_width * image_height * 0.25:
        raise ValueError("수동 모서리가 만드는 페이지 영역이 지나치게 작습니다.")
    side_lengths = [
        float(np.linalg.norm(ordered[(index + 1) % 4] - ordered[index]))
        for index in range(4)
    ]
    if min(side_lengths) < min(image_width, image_height) * 0.35:
        raise ValueError("수동 모서리 사이의 거리가 지나치게 짧습니다.")
    return ordered
