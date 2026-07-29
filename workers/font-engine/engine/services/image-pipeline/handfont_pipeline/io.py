from __future__ import annotations

from pathlib import Path

import cv2
import fitz
import numpy as np

from .errors import InputError


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff", ".bmp"}


def read_input(path: Path | str, *, pdf_page: int | None = None, render_dpi: int = 300) -> np.ndarray:
    input_path = Path(path)
    if not input_path.exists():
        raise InputError(f"입력 파일이 없습니다: {input_path}")

    suffix = input_path.suffix.lower()
    if suffix == ".pdf":
        if pdf_page is None:
            raise InputError("PDF 입력에는 1부터 시작하는 --pdf-page 값이 필요합니다.")
        document = fitz.open(input_path)
        try:
            if pdf_page < 1 or pdf_page > len(document):
                raise InputError(f"PDF 페이지 범위를 벗어났습니다: {pdf_page}/{len(document)}")
            page = document[pdf_page - 1]
            scale = render_dpi / 72.0
            pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
            array = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
            if pix.n == 4:
                return cv2.cvtColor(array, cv2.COLOR_RGBA2BGR)
            return cv2.cvtColor(array, cv2.COLOR_RGB2BGR)
        finally:
            document.close()

    if suffix not in IMAGE_EXTENSIONS:
        raise InputError(f"지원하지 않는 입력 형식입니다: {suffix}")
    data = np.fromfile(str(input_path), dtype=np.uint8)
    image = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if image is None:
        raise InputError(f"이미지를 읽지 못했습니다: {input_path}")
    return image


def write_image(path: Path | str, image: np.ndarray) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    suffix = output_path.suffix.lower() or ".png"
    ok, buffer = cv2.imencode(suffix, image)
    if not ok:
        raise InputError(f"이미지 인코딩에 실패했습니다: {output_path}")
    buffer.tofile(str(output_path))
    return output_path
