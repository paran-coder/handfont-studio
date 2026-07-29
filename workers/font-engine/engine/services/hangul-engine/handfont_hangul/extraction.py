from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

import cv2
import numpy as np

from .decomposition import decompose_syllable, layout_regions


def foreground_bbox(mask: np.ndarray) -> tuple[int, int, int, int]:
    ys, xs = np.where(mask > 0)
    if len(xs) == 0:
        raise ValueError("빈 마스크에서는 한글 위치 영역을 추출할 수 없습니다.")
    return int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1


def _pixel_box(normalized, glyph_bbox: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    gx0, gy0, gx1, gy1 = glyph_bbox
    width = max(1, gx1 - gx0)
    height = max(1, gy1 - gy0)
    x0 = gx0 + int(round(normalized.x0 * width))
    y0 = gy0 + int(round(normalized.y0 * height))
    x1 = gx0 + int(round(normalized.x1 * width))
    y1 = gy0 + int(round(normalized.y1 * height))
    return max(gx0, x0), max(gy0, y0), min(gx1, x1), min(gy1, y1)


def extract_position_regions(character: str, mask: np.ndarray, output_dir: Path | None = None) -> dict:
    decomposition = decompose_syllable(character)
    glyph_bbox = foreground_bbox(mask)
    regions = layout_regions(decomposition)
    output_dir and output_dir.mkdir(parents=True, exist_ok=True)
    total_ink = int(np.count_nonzero(mask))
    component_results = []
    for role, normalized in regions.items():
        x0, y0, x1, y1 = _pixel_box(normalized, glyph_bbox)
        crop = np.zeros_like(mask)
        crop[y0:y1, x0:x1] = mask[y0:y1, x0:x1]
        ink = int(np.count_nonzero(crop))
        observed_bbox = None
        if ink:
            observed_bbox = foreground_bbox(crop)
        path = None
        if output_dir is not None:
            path = output_dir / f"{role}.png"
            if not cv2.imwrite(str(path), crop):
                raise OSError(f"영역 마스크를 저장하지 못했습니다: {path}")
        jamo = getattr(decomposition, role)
        form = getattr(decomposition, f"{role}_form")
        component_results.append(
            {
                "role": role,
                "jamo": jamo,
                "form_id": form,
                "normalized_region": asdict(normalized),
                "pixel_region": [x0, y0, x1, y1],
                "observed_ink_bbox": list(observed_bbox) if observed_bbox else None,
                "ink_pixels": ink,
                "ink_coverage_of_glyph": round(ink / max(total_ink, 1), 6),
                "mask": path.name if path else None,
            }
        )
    return {
        "character": character,
        "codepoint": f"U+{ord(character):04X}",
        "decomposition": asdict(decomposition),
        "glyph_ink_bbox": list(glyph_bbox),
        "glyph_ink_pixels": total_ink,
        "components": component_results,
        "method": "overlapping-layout-region-v1",
        "warning": "영역 마스크는 위치형 학습용 휴리스틱이며 획 단위의 완전한 자모 분리는 아닙니다.",
    }
