from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import cv2
import numpy as np

from .compat import HANGUL_ENGINE_ROOT, IMAGE_PIPELINE_ROOT, VECTORIZER_ROOT  # noqa: F401
from .coverage import analyze_position_coverage
from .identifier import PageIdentifier
from .manual import load_manual_corners, validate_manual_corners
from .models import CaptureCandidate, SessionOptions
from .quality import capture_quality
from handfont_pipeline.config import DEFAULT_BLANK_DIR, DEFAULT_LAYOUT_PATH, DEFAULT_MAPPING_PATH, load_layout
from handfont_pipeline.io import read_input
from handfont_pipeline.markers import detect_markers
from handfont_pipeline.models import ProcessOptions
from handfont_pipeline.perspective import rectify_page
from handfont_pipeline.pipeline import process_page
from handfont_vectorizer.errors import EmptyMaskError, VectorizerError
from handfont_vectorizer.models import VectorizeOptions
from handfont_vectorizer.pipeline import vectorize_mask

SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff"}
DEFAULT_POSITION_MAP = HANGUL_ENGINE_ROOT / "examples" / "hangul-source-v1.6.0" / "hangul-position-map.json"


def _input_files(input_paths: Iterable[Path | str]) -> list[Path]:
    found: list[Path] = []
    for value in input_paths:
        path = Path(value)
        if path.is_dir():
            found.extend(item for item in sorted(path.iterdir()) if item.suffix.lower() in SUPPORTED_EXTENSIONS)
        elif path.suffix.lower() in SUPPORTED_EXTENSIONS:
            found.append(path)
    unique: list[Path] = []
    seen: set[Path] = set()
    for path in found:
        resolved = path.resolve()
        if resolved not in seen:
            seen.add(resolved)
            unique.append(path)
    return unique


def _manual_for(path: Path, manual: dict[str, np.ndarray]) -> np.ndarray | None:
    for key in (path.name, path.stem, str(path), str(path.resolve())):
        if key in manual:
            return manual[key]
    return None


def _write_json(path: Path, payload: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _build_overview(candidates: list[CaptureCandidate], selected: dict[int, CaptureCandidate], output: Path) -> Path | None:
    if not candidates:
        return None
    tile_w, tile_h = 280, 360
    cols = 3
    rows = (len(candidates) + cols - 1) // cols
    canvas = np.full((rows * tile_h, cols * tile_w, 3), 248, dtype=np.uint8)
    for index, candidate in enumerate(candidates):
        image = cv2.imread(str(candidate.input_path), cv2.IMREAD_COLOR)
        if image is None:
            continue
        image = cv2.resize(image, (240, 285), interpolation=cv2.INTER_AREA)
        x = (index % cols) * tile_w + 20
        y = (index // cols) * tile_h + 15
        canvas[y:y + 285, x:x + 240] = image
        is_selected = selected.get(candidate.page) is candidate
        marker = "SELECTED" if is_selected else "DUPLICATE"
        text = f"P{candidate.page:02d} {marker} {candidate.marker_method}"
        cv2.putText(canvas, text, (x, y + 310), cv2.FONT_HERSHEY_SIMPLEX, 0.46, (20, 20, 20), 1, cv2.LINE_AA)
        cv2.putText(canvas, f"score={candidate.capture_score:.3f} id={candidate.page_identification.confidence:.3f}", (x, y + 334), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (40, 40, 40), 1, cv2.LINE_AA)
    output.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(output), canvas)
    return output


def process_capture_session(
    input_paths: Iterable[Path | str],
    output_dir: Path | str,
    options: SessionOptions = SessionOptions(),
    *,
    manual_corners_path: Path | str | None = None,
    layout_path: Path | str = DEFAULT_LAYOUT_PATH,
    mapping_path: Path | str = DEFAULT_MAPPING_PATH,
    blank_dir: Path | str = DEFAULT_BLANK_DIR,
    position_map_path: Path | str = DEFAULT_POSITION_MAP,
) -> dict[str, Any]:
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    files = _input_files(input_paths)
    if not files:
        raise ValueError("처리할 촬영 이미지가 없습니다.")
    manual = load_manual_corners(manual_corners_path)
    layout = load_layout(layout_path)
    identifier = PageIdentifier(blank_dir=blank_dir, layout_path=layout_path, dpi=options.dpi)

    candidates: list[CaptureCandidate] = []
    failures: list[dict[str, str]] = []
    for path in files:
        try:
            image = read_input(path, render_dpi=options.dpi)
            height, width = image.shape[:2]
            marker_method = "automatic"
            try:
                marker = detect_markers(image)
                points = marker.points
                marker_confidence = marker.confidence
            except Exception as automatic_error:
                manual_points = _manual_for(path, manual)
                if manual_points is None:
                    raise RuntimeError(f"자동 마커 검출 실패 및 수동 좌표 없음: {automatic_error}") from automatic_error
                points = validate_manual_corners(manual_points, width, height)
                marker_confidence = 1.0
                marker_method = "manual"
            rectified, _ = rectify_page(image, points, layout, options.dpi)
            identification = identifier.identify(rectified)
            if identification.confidence < options.min_page_confidence:
                raise RuntimeError(
                    f"페이지 식별 신뢰도가 낮습니다: page={identification.page}, confidence={identification.confidence:.3f}"
                )
            sharpness, exposure, score, warnings = capture_quality(
                image, marker_confidence, identification.confidence, marker_method
            )
            candidates.append(CaptureCandidate(
                input_path=path,
                page=identification.page,
                marker_points=points,
                marker_method=marker_method,
                marker_confidence=marker_confidence,
                page_identification=identification,
                sharpness=sharpness,
                exposure=exposure,
                capture_score=score,
                original_size=(width, height),
                warnings=warnings,
            ))
        except Exception as error:
            failures.append({"input": str(path), "error": str(error)})

    grouped: dict[int, list[CaptureCandidate]] = defaultdict(list)
    for candidate in candidates:
        grouped[candidate.page].append(candidate)
    selected: dict[int, CaptureCandidate] = {
        page: max(items, key=lambda item: (item.capture_score, item.page_identification.margin, item.sharpness))
        for page, items in grouped.items()
    }
    expected = set(options.expected_pages)
    missing_pages = sorted(expected - set(selected))
    duplicate_pages = {
        str(page): [item.to_dict() for item in sorted(items, key=lambda item: item.capture_score, reverse=True)]
        for page, items in grouped.items() if len(items) > 1
    }

    page_metadata: list[dict[str, Any]] = []
    vector_records: list[dict[str, Any]] = []
    vector_failures: list[dict[str, str]] = []
    vectorized = 0
    for page in sorted(selected):
        candidate = selected[page]
        page_dir = output_root / "pages" / f"page-{page:02d}"
        result = process_page(
            candidate.input_path,
            page_dir,
            ProcessOptions(template_page=page, output_dpi=options.dpi),
            layout_path=layout_path,
            mapping_path=mapping_path,
            blank_dir=blank_dir,
            source_points=candidate.marker_points,
            marker_method=candidate.marker_method,
        )
        metadata = json.loads(result.metadata_path.read_text(encoding="utf-8"))
        metadata["capture"] = candidate.to_dict()
        result.metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
        page_metadata.append(metadata)

        if options.vectorize:
            for cell in metadata["cells"]:
                status = cell.get("quality", {}).get("status")
                if status not in {"ok", "too_dense"}:
                    continue
                if options.vectorize_limit is not None and vectorized >= options.vectorize_limit:
                    break
                mask_rel = cell.get("files", {}).get("ink_mask")
                if not mask_rel:
                    continue
                mask_path = page_dir / mask_rel
                vector_dir = output_root / "vectors" / cell["cell_id"]
                try:
                    vector = vectorize_mask(
                        mask_path,
                        vector_dir,
                        VectorizeOptions(minimum_component_area=5, target_raster_iou=0.88),
                        title=f"{cell.get('character', '')} {cell['cell_id']}",
                    )
                    vector_records.append({
                        "cell_id": cell["cell_id"],
                        "character": cell.get("character", ""),
                        "svg": str(vector.svg_path.relative_to(output_root)),
                        "raster_iou": round(vector.iou, 6),
                        "contours": vector.contour_count,
                    })
                    vectorized += 1
                except EmptyMaskError as error:
                    vector_failures.append({"cell_id": cell["cell_id"], "error": str(error), "type": "skipped"})
                except (VectorizerError, Exception) as error:
                    vector_failures.append({"cell_id": cell["cell_id"], "error": str(error), "type": "failed"})
            if options.vectorize_limit is not None and vectorized >= options.vectorize_limit:
                continue

    coverage = analyze_position_coverage(page_metadata, position_map_path)
    _write_json(output_root / "position-coverage.json", coverage)
    overview_path = _build_overview(candidates, selected, output_root / "capture-overview.png")

    status_counts: dict[str, int] = defaultdict(int)
    for metadata in page_metadata:
        for status, count in metadata.get("summary", {}).get("status_counts", {}).items():
            status_counts[status] += int(count)

    summary = {
        "schema_version": "1.8.0",
        "processed_at": datetime.now(timezone.utc).isoformat(),
        "input_files": len(files),
        "recognized_candidates": len(candidates),
        "failed_inputs": len(failures),
        "selected_pages": sorted(selected),
        "missing_pages": missing_pages,
        "duplicate_pages": sorted(int(page) for page in duplicate_pages),
        "manual_pages": sorted(page for page, item in selected.items() if item.marker_method == "manual"),
        "complete": not missing_pages and not failures,
        "cell_status_counts": dict(status_counts),
        "vectorization": {
            "processed": len(vector_records),
            "failed_or_skipped": len(vector_failures),
            "limit": options.vectorize_limit,
            "records": vector_records,
            "failures": vector_failures,
        },
        "position_coverage": {
            key: coverage[key]
            for key in (
                "expected_position_forms", "covered_position_forms", "review_position_forms",
                "missing_position_forms", "coverage_ratio", "clean_coverage_ratio"
            )
        },
        "files": {
            "capture_overview": str(overview_path.relative_to(output_root)) if overview_path else None,
            "position_coverage": "position-coverage.json",
        },
        "candidates": [item.to_dict() for item in candidates],
        "selected": {str(page): item.to_dict() for page, item in selected.items()},
        "duplicates": duplicate_pages,
        "failures": failures,
    }
    _write_json(output_root / "session-summary.json", summary)
    return summary
