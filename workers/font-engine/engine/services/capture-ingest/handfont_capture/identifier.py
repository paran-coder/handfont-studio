from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from .compat import IMAGE_PIPELINE_ROOT  # noqa: F401
from .models import PageIdentification
from handfont_pipeline.cells import normalized_box_to_pixels, relative_roi_to_pixels
from handfont_pipeline.config import DEFAULT_BLANK_DIR, DEFAULT_LAYOUT_PATH, load_cells, load_layout
from handfont_pipeline.perspective import canonical_size


class PageIdentifier:
    def __init__(
        self,
        blank_dir: Path | str = DEFAULT_BLANK_DIR,
        layout_path: Path | str = DEFAULT_LAYOUT_PATH,
        dpi: int = 150,
    ) -> None:
        self.blank_dir = Path(blank_dir)
        self.layout = load_layout(layout_path)
        self.dpi = dpi
        self.width, self.height = canonical_size(dpi)
        references: list[np.ndarray] = []
        for page in range(1, 10):
            path = self.blank_dir / f"template-page-{page:02d}.png"
            image = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
            if image is None:
                raise FileNotFoundError(f"페이지 식별용 빈 템플릿을 읽지 못했습니다: {path}")
            references.append(cv2.resize(image, (self.width, self.height), interpolation=cv2.INTER_AREA))
        self.references = references
        self.mask = self._build_discriminative_mask()

    def _build_discriminative_mask(self) -> np.ndarray:
        keep = np.full((self.height, self.width), 255, dtype=np.uint8)
        for cell in load_cells(self.layout):
            x, y, w, h = normalized_box_to_pixels(cell.box_norm, self.width, self.height)
            left, top, right, bottom = relative_roi_to_pixels(cell.writing_roi_norm, w, h)
            cv2.rectangle(keep, (x + left, y + top), (x + right, y + bottom), 0, -1)
        stack = np.stack(self.references).astype(np.float32)
        variation = stack.std(axis=0)
        darkest = stack.min(axis=0)
        mask = ((variation > 4.0) & (keep > 0) & (darkest < 245)).astype(np.uint8) * 255
        mask = cv2.dilate(mask, np.ones((3, 3), dtype=np.uint8), iterations=1)
        if np.count_nonzero(mask) < 5000:
            raise RuntimeError("페이지 식별 마스크가 충분한 구분 픽셀을 포함하지 않습니다.")
        return mask.astype(bool)

    def identify(self, rectified: np.ndarray) -> PageIdentification:
        gray = cv2.cvtColor(rectified, cv2.COLOR_BGR2GRAY) if rectified.ndim == 3 else rectified
        if gray.shape != (self.height, self.width):
            gray = cv2.resize(gray, (self.width, self.height), interpolation=cv2.INTER_AREA)
        candidate = gray.astype(np.float32)
        scores: dict[int, float] = {}
        for page, reference in enumerate(self.references, start=1):
            difference = np.abs(candidate - reference.astype(np.float32))
            score = 1.0 - float(np.mean(difference[self.mask])) / 255.0
            scores[page] = score
        ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
        best_page, best_score = ranked[0]
        second_score = ranked[1][1]
        margin = best_score - second_score
        absolute = max(0.0, min(1.0, (best_score - 0.68) / 0.20))
        separation = max(0.0, min(1.0, margin / 0.04))
        confidence = 0.45 * absolute + 0.55 * separation
        return PageIdentification(
            page=best_page,
            score=best_score,
            second_score=second_score,
            margin=margin,
            confidence=confidence,
            scores=scores,
        )
