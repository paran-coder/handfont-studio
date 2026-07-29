from __future__ import annotations

import json
from datetime import datetime, timezone
from dataclasses import replace
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from .geometry import extract_vector_contours
from .io import read_mask_image, write_image
from .mask import normalize_mask
from .models import VectorizeOptions, VectorizeResult
from .quality import difference_image, mask_iou, overlay_image, rasterize_svg
from .svg import build_svg


def _json_default(value: Any) -> Any:
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, Path):
        return str(value)
    raise TypeError(f"직렬화할 수 없는 값입니다: {type(value)!r}")


def vectorize_mask(
    input_path: Path | str,
    output_dir: Path | str,
    options: VectorizeOptions = VectorizeOptions(),
    *,
    title: str | None = None,
) -> VectorizeResult:
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    source = read_mask_image(input_path)
    mask, normalization = normalize_mask(source, options)
    height, width = mask.shape
    best: tuple[float, list, str, np.ndarray, float] | None = None
    tolerance = options.simplify_tolerance
    refinement_count = 0
    for refinement in range(max(0, options.max_refinements) + 1):
        effective_options = replace(options, simplify_tolerance=tolerance)
        candidate_contours = extract_vector_contours(mask, effective_options)
        candidate_svg = build_svg(candidate_contours, width, height, title=title or Path(input_path).stem)
        candidate_raster = rasterize_svg(candidate_svg, width, height)
        candidate_iou = mask_iou(mask, candidate_raster)
        if best is None or candidate_iou > best[0]:
            best = (candidate_iou, candidate_contours, candidate_svg, candidate_raster, tolerance)
            refinement_count = refinement
        if candidate_iou >= options.target_raster_iou:
            best = (candidate_iou, candidate_contours, candidate_svg, candidate_raster, tolerance)
            refinement_count = refinement
            break
        tolerance *= 0.75

    assert best is not None
    iou, contours, svg, raster, effective_tolerance = best

    original_nodes = sum(len(contour.original_points) for contour in contours)
    simplified_nodes = sum(len(contour.simplified_points) for contour in contours)
    node_reduction_ratio = 1.0 - simplified_nodes / float(max(original_nodes, 1))
    contour_area = sum(contour.area * (-1.0 if contour.is_hole else 1.0) for contour in contours)

    svg_path = output_root / "glyph.svg"
    svg_path.write_text(svg, encoding="utf-8")
    original_path = write_image(output_root / "original-mask.png", mask)
    raster_path = write_image(output_root / "vector-raster.png", raster)
    difference_path = write_image(output_root / "difference.png", difference_image(mask, raster))
    overlay_path = write_image(output_root / "overlay.png", overlay_image(mask, raster))

    metadata = {
        "schema_version": "1.4.0",
        "processed_at": datetime.now(timezone.utc).isoformat(),
        "input": {
            "path": str(Path(input_path)),
            "title": title or Path(input_path).stem,
        },
        "normalization": normalization,
        "options": {
            "minimum_component_area": options.minimum_component_area,
            "close_kernel": options.close_kernel,
            "simplify_tolerance_requested": options.simplify_tolerance,
            "simplify_tolerance_effective": round(effective_tolerance, 8),
            "refinement_count": refinement_count,
            "target_raster_iou": options.target_raster_iou,
            "corner_angle_degrees": options.corner_angle_degrees,
            "smoothing_radius": options.smoothing_radius,
            "coordinate_precision": options.coordinate_precision,
        },
        "summary": {
            "contours": len(contours),
            "outer_contours": sum(not contour.is_hole for contour in contours),
            "hole_contours": sum(contour.is_hole for contour in contours),
            "original_nodes": original_nodes,
            "simplified_nodes": simplified_nodes,
            "node_reduction_ratio": round(node_reduction_ratio, 6),
            "path_commands": sum(contour.path_commands for contour in contours),
            "signed_contour_area": round(contour_area, 3),
            "raster_iou": round(iou, 6),
            "status": "ok" if iou >= 0.90 else "review",
        },
        "contours": [
            {
                "index": contour.index,
                "parent": contour.parent,
                "depth": contour.depth,
                "is_hole": contour.is_hole,
                "area": round(contour.area, 3),
                "original_points": len(contour.original_points),
                "simplified_points": len(contour.simplified_points),
                "path_commands": contour.path_commands,
            }
            for contour in contours
        ],
        "files": {
            "svg": str(svg_path.relative_to(output_root)),
            "original_mask": str(original_path.relative_to(output_root)),
            "vector_raster": str(raster_path.relative_to(output_root)),
            "difference": str(difference_path.relative_to(output_root)),
            "overlay": str(overlay_path.relative_to(output_root)),
        },
    }
    metadata_path = output_root / "metadata.json"
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2, default=_json_default), encoding="utf-8")

    return VectorizeResult(
        output_dir=output_root,
        svg_path=svg_path,
        metadata_path=metadata_path,
        raster_path=raster_path,
        difference_path=difference_path,
        iou=iou,
        contour_count=len(contours),
        node_reduction_ratio=node_reduction_ratio,
    )
