from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np


@dataclass(frozen=True)
class PageIdentification:
    page: int
    score: float
    second_score: float
    margin: float
    confidence: float
    scores: dict[int, float]


@dataclass
class CaptureCandidate:
    input_path: Path
    page: int
    marker_points: np.ndarray
    marker_method: str
    marker_confidence: float
    page_identification: PageIdentification
    sharpness: float
    exposure: float
    capture_score: float
    original_size: tuple[int, int]
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "input": str(self.input_path),
            "page": self.page,
            "marker_method": self.marker_method,
            "marker_confidence": round(self.marker_confidence, 6),
            "marker_points": self.marker_points.round(3).tolist(),
            "page_identification": {
                "score": round(self.page_identification.score, 6),
                "second_score": round(self.page_identification.second_score, 6),
                "margin": round(self.page_identification.margin, 6),
                "confidence": round(self.page_identification.confidence, 6),
                "scores": {str(key): round(value, 6) for key, value in self.page_identification.scores.items()},
            },
            "sharpness": round(self.sharpness, 6),
            "exposure": round(self.exposure, 6),
            "capture_score": round(self.capture_score, 6),
            "original_size": list(self.original_size),
            "warnings": self.warnings,
        }


@dataclass(frozen=True)
class SessionOptions:
    dpi: int = 150
    expected_pages: tuple[int, ...] = tuple(range(1, 10))
    vectorize: bool = True
    vectorize_limit: int | None = 64
    min_page_confidence: float = 0.35
