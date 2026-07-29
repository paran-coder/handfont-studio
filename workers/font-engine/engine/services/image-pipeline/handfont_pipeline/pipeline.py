from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from .cells import draw_overlay, extract_cells
from .config import DEFAULT_BLANK_DIR, DEFAULT_LAYOUT_PATH, DEFAULT_MAPPING_PATH, load_cells, load_layout
from .errors import InputError
from .ink import extract_ink_mask, render_ink
from .io import read_input, write_image
from .mapping import load_page_mapping
from .markers import detect_markers, order_points
from .models import ProcessOptions, ProcessResult
from .perspective import rectify_page


def _blank_page_path(blank_dir: Path, template_page: int) -> Path:
    return blank_dir / f"template-page-{template_page:02d}.png"


def _json_default(value: Any) -> Any:
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, Path):
        return str(value)
    raise TypeError(f"직렬화할 수 없는 값입니다: {type(value)!r}")


def process_page(
    input_path: Path | str,
    output_dir: Path | str,
    options: ProcessOptions,
    *,
    pdf_page: int | None = None,
    layout_path: Path | str = DEFAULT_LAYOUT_PATH,
    mapping_path: Path | str = DEFAULT_MAPPING_PATH,
    blank_dir: Path | str = DEFAULT_BLANK_DIR,
    source_points: np.ndarray | list[list[float]] | None = None,
    marker_method: str = "automatic",
) -> ProcessResult:
    if not 1 <= options.template_page <= 9:
        raise InputError("template_page는 1부터 9까지여야 합니다.")

    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    layout = load_layout(layout_path)
    cells = load_cells(layout)
    mapping = load_page_mapping(mapping_path, options.template_page)

    image = read_input(input_path, pdf_page=pdf_page, render_dpi=options.output_dpi)
    if source_points is None:
        marker_result = detect_markers(image)
        marker_points = marker_result.points
        marker_confidence = marker_result.confidence
        marker_candidates = marker_result.candidates
        effective_marker_method = "automatic"
    else:
        marker_points = order_points(np.asarray(source_points, dtype=np.float32))
        if marker_points.shape != (4, 2):
            raise InputError("source_points는 좌상·우상·우하·좌하를 나타내는 4x2 좌표여야 합니다.")
        marker_confidence = 1.0
        marker_candidates = []
        effective_marker_method = marker_method or "manual"
    rectified, transform = rectify_page(image, marker_points, layout, options.output_dpi)

    blank_path = _blank_page_path(Path(blank_dir), options.template_page)
    if not blank_path.exists():
        raise InputError(f"빈 템플릿 기준 이미지가 없습니다: {blank_path}")
    blank = cv2.imread(str(blank_path), cv2.IMREAD_COLOR)
    if blank is None:
        raise InputError(f"빈 템플릿 기준 이미지를 읽지 못했습니다: {blank_path}")
    if blank.shape[:2] != rectified.shape[:2]:
        blank = cv2.resize(blank, (rectified.shape[1], rectified.shape[0]), interpolation=cv2.INTER_AREA)

    extracted = extract_cells(rectified, cells)
    blank_cells = extract_cells(blank, cells)
    blank_by_id = {item["layout"].cell_id: item for item in blank_cells}
    for item in extracted:
        item["cell_id"] = f"P{options.template_page:02d}-{item['layout'].cell_id}"

    cells_dir = output_root / "cells"
    cells_dir.mkdir(parents=True, exist_ok=True)
    metadata_cells: list[dict[str, Any]] = []
    statuses: dict[str, str] = {}

    for item in extracted:
        slot_id = item["layout"].cell_id
        cell_id = item["cell_id"]
        blank_item = blank_by_id[slot_id]
        mask, quality = extract_ink_mask(
            item["writing"],
            blank_item["writing"],
            minimum_area=max(1, int(round(options.min_component_area * options.output_dpi / 300.0))),
        )
        statuses[cell_id] = quality["status"]
        cell_dir = cells_dir / cell_id
        cell_dir.mkdir(parents=True, exist_ok=True)
        files: dict[str, str] = {}
        if options.save_full_cells:
            files["cell"] = str(write_image(cell_dir / "cell.png", item["cell"]).relative_to(output_root))
        if options.save_writing_rois:
            files["writing"] = str(write_image(cell_dir / "writing.png", item["writing"]).relative_to(output_root))
        if options.save_masks:
            files["ink_mask"] = str(write_image(cell_dir / "ink-mask.png", mask).relative_to(output_root))
            files["ink"] = str(write_image(cell_dir / "ink.png", render_ink(mask)).relative_to(output_root))

        character_info = mapping.get(cell_id, {})
        metadata_cells.append(
            {
                "cell_id": cell_id,
                "index": item["layout"].index,
                "character": character_info.get("character", ""),
                "unicode": character_info.get("unicode", ""),
                "category": character_info.get("category", "예비"),
                "subgroup": character_info.get("subgroup", "예비 칸"),
                "generation_role": character_info.get("generation_role", "user-defined"),
                "box_px": item["box_px"],
                "writing_roi_px": item["writing_roi_px"],
                "quality": quality,
                "files": files,
            }
        )

    rectified_path = write_image(output_root / "rectified.png", rectified)
    overlay_path = write_image(output_root / "overlay.png", draw_overlay(rectified, extracted, statuses))
    marker_debug = image.copy()
    for index, point in enumerate(marker_points):
        center = tuple(int(round(value)) for value in point)
        cv2.circle(marker_debug, center, max(8, int(round(min(image.shape[:2]) * 0.006))), (0, 0, 255), 4)
        cv2.putText(marker_debug, str(index + 1), (center[0] + 10, center[1] - 10), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 3, cv2.LINE_AA)
    marker_debug_path = write_image(output_root / "marker-debug.png", marker_debug)

    status_counts: dict[str, int] = {}
    for status in statuses.values():
        status_counts[status] = status_counts.get(status, 0) + 1

    metadata = {
        "schema_version": "1.3.0",
        "processed_at": datetime.now(timezone.utc).isoformat(),
        "input": {
            "path": str(Path(input_path)),
            "pdf_page": pdf_page,
            "template_page": options.template_page,
            "original_size": [int(image.shape[1]), int(image.shape[0])],
        },
        "output": {
            "dpi": options.output_dpi,
            "size": [int(rectified.shape[1]), int(rectified.shape[0])],
            "rectified": str(rectified_path.relative_to(output_root)),
            "overlay": str(overlay_path.relative_to(output_root)),
            "marker_debug": str(marker_debug_path.relative_to(output_root)),
        },
        "markers": {
            "method": effective_marker_method,
            "confidence": round(marker_confidence, 6),
            "points": marker_points.round(3).tolist(),
            "candidates": marker_candidates,
            "homography": transform.round(8).tolist(),
        },
        "summary": {
            "cells": len(metadata_cells),
            "status_counts": status_counts,
        },
        "cells": metadata_cells,
    }
    metadata_path = output_root / "metadata.json"
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2, default=_json_default), encoding="utf-8")

    return ProcessResult(
        output_dir=output_root,
        metadata_path=metadata_path,
        rectified_path=rectified_path,
        overlay_path=overlay_path,
        marker_confidence=marker_confidence,
        cells_written=len(metadata_cells),
    )
