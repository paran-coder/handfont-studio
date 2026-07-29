from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np
import pytest

from handfont_vectorizer.errors import InputMaskError
from handfont_vectorizer.io import write_image
from handfont_vectorizer.models import VectorizeOptions
from handfont_vectorizer.pipeline import vectorize_mask
from handfont_vectorizer.quality import rasterize_svg


def _base(size: int = 256) -> np.ndarray:
    return np.zeros((size, size), dtype=np.uint8)


def test_empty_mask_fails(tmp_path: Path) -> None:
    path = write_image(tmp_path / "empty.png", _base())
    with pytest.raises(InputMaskError):
        vectorize_mask(path, tmp_path / "out")


def test_white_background_black_ink_is_inferred(tmp_path: Path) -> None:
    image = np.full((220, 220), 255, dtype=np.uint8)
    cv2.line(image, (40, 35), (40, 180), 0, 22, cv2.LINE_AA)
    cv2.line(image, (40, 50), (170, 50), 0, 22, cv2.LINE_AA)
    path = write_image(tmp_path / "dark-on-light.png", image)
    result = vectorize_mask(path, tmp_path / "out")
    metadata = json.loads(result.metadata_path.read_text(encoding="utf-8"))
    assert metadata["normalization"]["foreground_is_bright"] is False
    assert result.iou >= 0.90


def test_hole_is_preserved(tmp_path: Path) -> None:
    mask = _base()
    cv2.circle(mask, (128, 128), 82, 255, -1, cv2.LINE_AA)
    cv2.circle(mask, (128, 128), 38, 0, -1, cv2.LINE_AA)
    path = write_image(tmp_path / "ring.png", mask)
    result = vectorize_mask(path, tmp_path / "out", VectorizeOptions(simplify_tolerance=0.0018))
    metadata = json.loads(result.metadata_path.read_text(encoding="utf-8"))
    raster = cv2.imread(str(result.raster_path), cv2.IMREAD_GRAYSCALE)
    assert metadata["summary"]["hole_contours"] >= 1
    assert raster[128, 128] == 0
    assert result.iou >= 0.93


def test_disconnected_components_and_node_reduction(tmp_path: Path) -> None:
    mask = _base(320)
    cv2.rectangle(mask, (35, 55), (110, 265), 255, -1)
    cv2.rectangle(mask, (110, 55), (250, 105), 255, -1)
    cv2.ellipse(mask, (225, 210), (50, 60), 0, 0, 360, 255, -1, cv2.LINE_AA)
    path = write_image(tmp_path / "components.png", mask)
    result = vectorize_mask(path, tmp_path / "out")
    assert result.contour_count >= 2
    assert result.node_reduction_ratio >= 0.50
    assert result.iou >= 0.90


def test_svg_has_quadratic_bezier_and_evenodd(tmp_path: Path) -> None:
    mask = _base()
    points = np.array([[45, 200], [70, 60], [130, 35], [210, 90], [180, 210], [120, 170]], np.int32)
    cv2.fillPoly(mask, [points], 255, lineType=cv2.LINE_AA)
    path = write_image(tmp_path / "shape.png", mask)
    result = vectorize_mask(path, tmp_path / "out")
    svg = result.svg_path.read_text(encoding="utf-8")
    assert "fill-rule=\"evenodd\"" in svg
    assert " Q " in svg
    raster = rasterize_svg(svg, mask.shape[1], mask.shape[0])
    assert raster.shape == mask.shape


def test_metadata_schema_and_files(tmp_path: Path) -> None:
    mask = _base(180)
    cv2.putText(mask, "8", (35, 145), cv2.FONT_HERSHEY_SIMPLEX, 4.2, 255, 12, cv2.LINE_AA)
    path = write_image(tmp_path / "eight.png", mask)
    result = vectorize_mask(path, tmp_path / "out")
    metadata = json.loads(result.metadata_path.read_text(encoding="utf-8"))
    assert metadata["schema_version"] == "1.4.0"
    assert metadata["summary"]["raster_iou"] >= 0.90
    assert (tmp_path / "out" / metadata["files"]["difference"]).exists()
    assert (tmp_path / "out" / metadata["files"]["overlay"]).exists()


def test_dimensions_are_preserved(tmp_path: Path) -> None:
    mask = np.zeros((173, 241), dtype=np.uint8)
    cv2.ellipse(mask, (120, 86), (70, 45), 15, 0, 360, 255, -1, cv2.LINE_AA)
    path = write_image(tmp_path / "ellipse.png", mask)
    result = vectorize_mask(path, tmp_path / "out")
    raster = cv2.imread(str(result.raster_path), cv2.IMREAD_GRAYSCALE)
    assert raster.shape == mask.shape
    svg = result.svg_path.read_text(encoding="utf-8")
    assert 'viewBox="0 0 241 173"' in svg


def test_svg_output_is_deterministic(tmp_path: Path) -> None:
    mask = _base(200)
    cv2.line(mask, (25, 30), (170, 155), 255, 17, cv2.LINE_AA)
    path = write_image(tmp_path / "stroke.png", mask)
    first = vectorize_mask(path, tmp_path / "first")
    second = vectorize_mask(path, tmp_path / "second")
    assert first.svg_path.read_bytes() == second.svg_path.read_bytes()


@pytest.mark.parametrize("cell_number", range(1, 9))
def test_image_pipeline_written_cells_meet_iou(cell_number: int, tmp_path: Path) -> None:
    project_root = Path(__file__).resolve().parents[2]
    mask_path = (
        project_root
        / "image-pipeline"
        / "examples"
        / "synthetic-page-01"
        / "cells"
        / f"P01-C{cell_number:02d}"
        / "ink-mask.png"
    )
    assert mask_path.exists()
    result = vectorize_mask(mask_path, tmp_path / f"cell-{cell_number:02d}")
    assert result.iou >= 0.90
    assert result.node_reduction_ratio >= 0.50
