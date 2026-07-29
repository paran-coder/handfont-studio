from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from .errors import InputMaskError


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff", ".bmp"}


def read_mask_image(path: Path | str) -> np.ndarray:
    input_path = Path(path)
    if not input_path.exists():
        raise InputMaskError(f"입력 마스크가 없습니다: {input_path}")
    if input_path.suffix.lower() not in IMAGE_EXTENSIONS:
        raise InputMaskError(f"지원하지 않는 마스크 형식입니다: {input_path.suffix}")
    data = np.fromfile(str(input_path), dtype=np.uint8)
    image = cv2.imdecode(data, cv2.IMREAD_UNCHANGED)
    if image is None:
        raise InputMaskError(f"마스크 이미지를 읽지 못했습니다: {input_path}")
    return image


def write_image(path: Path | str, image: np.ndarray) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    suffix = output_path.suffix.lower() or ".png"
    ok, buffer = cv2.imencode(suffix, image)
    if not ok:
        raise InputMaskError(f"이미지 인코딩에 실패했습니다: {output_path}")
    buffer.tofile(str(output_path))
    return output_path
