from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np
import pytest

from handfont_pipeline.config import DEFAULT_BLANK_DIR, DEFAULT_LAYOUT_PATH, load_cells, load_layout
from handfont_pipeline.errors import MarkerDetectionError
from handfont_pipeline.markers import detect_markers
from handfont_pipeline.models import ProcessOptions
from handfont_pipeline.pipeline import process_page
from handfont_pipeline.perspective import canonical_size, rectify_page


@pytest.fixture(scope='session')
def layout() -> dict:
    return load_layout(DEFAULT_LAYOUT_PATH)


def test_layout_has_35_cells(layout: dict) -> None:
    cells = load_cells(layout)
    assert len(cells) == 35
    assert cells[0].cell_id == 'C01'
    assert cells[-1].cell_id == 'C35'


@pytest.mark.parametrize('page_number', range(1, 10))
def test_registration_markers_on_all_pristine_pages(page_number: int) -> None:
    image = cv2.imread(str(DEFAULT_BLANK_DIR / f'template-page-{page_number:02d}.png'))
    assert image is not None
    result = detect_markers(image)
    assert result.points.shape == (4, 2)
    assert result.confidence > 0.70


def test_rectification_size(layout: dict) -> None:
    image = cv2.imread(str(DEFAULT_BLANK_DIR / 'template-page-01.png'))
    markers = detect_markers(image)
    rectified, transform = rectify_page(image, markers.points, layout, 150)
    assert (rectified.shape[1], rectified.shape[0]) == canonical_size(150)
    assert transform.shape == (3, 3)


def test_pipeline_outputs_mapping_and_35_cells(tmp_path: Path) -> None:
    input_path = DEFAULT_BLANK_DIR / 'template-page-01.png'
    result = process_page(input_path, tmp_path / 'out', ProcessOptions(template_page=1, output_dpi=150))
    metadata = json.loads(result.metadata_path.read_text(encoding='utf-8'))
    assert metadata['summary']['cells'] == 35
    assert metadata['cells'][0]['cell_id'] == 'P01-C01'
    assert metadata['cells'][0]['character'] == '가'
    assert metadata['cells'][0]['unicode'] == 'U+AC00'
    assert metadata['summary']['status_counts']['missing'] == 35



def test_synthetic_ink_is_separated(tmp_path: Path, layout: dict) -> None:
    image = cv2.imread(str(DEFAULT_BLANK_DIR / 'template-page-01.png'))
    assert image is not None
    height, width = image.shape[:2]
    first = load_cells(layout)[0]
    x = int(round(first.box_norm[0] * width))
    y = int(round(first.box_norm[1] * height))
    w = int(round(first.box_norm[2] * width))
    h = int(round(first.box_norm[3] * height))
    left = int(round(first.writing_roi_norm[0] * w))
    top = int(round(first.writing_roi_norm[1] * h))
    right = int(round(first.writing_roi_norm[2] * w))
    bottom = int(round(first.writing_roi_norm[3] * h))
    points = np.array([
        [x + left + 35, y + top + 70],
        [x + left + 90, y + top + 25],
        [x + left + 150, y + top + 150],
        [x + right - 35, y + bottom - 45],
    ], dtype=np.int32)
    cv2.polylines(image, [points], False, (0, 0, 0), 12, cv2.LINE_AA)
    input_path = tmp_path / 'ink.png'
    cv2.imwrite(str(input_path), image)
    result = process_page(input_path, tmp_path / 'ink-out', ProcessOptions(template_page=1, output_dpi=150))
    metadata = json.loads(result.metadata_path.read_text(encoding='utf-8'))
    assert metadata['cells'][0]['quality']['status'] == 'ok'
    assert metadata['cells'][0]['quality']['foreground_pixels'] > 100
    assert metadata['cells'][1]['quality']['status'] == 'missing'

def test_missing_marker_fails() -> None:
    image = cv2.imread(str(DEFAULT_BLANK_DIR / 'template-page-01.png'))
    assert image is not None
    image[:180, :180] = 255
    with pytest.raises(MarkerDetectionError):
        detect_markers(image)
