from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class VectorizeOptions:
    threshold: int | None = None
    minimum_component_area: int = 12
    close_kernel: int = 3
    simplify_tolerance: float = 0.00085
    corner_angle_degrees: float = 110.0
    smoothing_radius: float = 0.05
    coordinate_precision: int = 2
    minimum_foreground_ratio: float = 0.0006
    maximum_foreground_ratio: float = 0.72
    target_raster_iou: float = 0.90
    max_refinements: int = 3


@dataclass(frozen=True)
class VectorizeResult:
    output_dir: Path
    svg_path: Path
    metadata_path: Path
    raster_path: Path
    difference_path: Path
    iou: float
    contour_count: int
    node_reduction_ratio: float
