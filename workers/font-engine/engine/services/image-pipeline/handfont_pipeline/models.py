from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np


@dataclass(frozen=True)
class MarkerResult:
    points: np.ndarray
    candidates: list[dict[str, Any]]
    confidence: float


@dataclass(frozen=True)
class CellLayout:
    index: int
    cell_id: str
    box_norm: tuple[float, float, float, float]
    writing_roi_norm: tuple[float, float, float, float]


@dataclass(frozen=True)
class ProcessOptions:
    template_page: int
    output_dpi: int = 300
    save_full_cells: bool = True
    save_writing_rois: bool = True
    save_masks: bool = True
    min_component_area: int = 18


@dataclass(frozen=True)
class ProcessResult:
    output_dir: Path
    metadata_path: Path
    rectified_path: Path
    overlay_path: Path
    marker_confidence: float
    cells_written: int
