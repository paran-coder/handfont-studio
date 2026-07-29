import numpy as np
import pytest

from handfont_capture.manual import validate_manual_corners


def test_manual_corners_are_ordered_and_validated():
    points = np.array([[900, 1100], [100, 100], [900, 100], [100, 1100]], dtype=np.float32)
    result = validate_manual_corners(points, 1000, 1200)
    assert result.tolist() == [[100.0, 100.0], [900.0, 100.0], [900.0, 1100.0], [100.0, 1100.0]]


def test_manual_corners_reject_small_polygon():
    points = np.array([[10, 10], [50, 10], [50, 50], [10, 50]], dtype=np.float32)
    with pytest.raises(ValueError):
        validate_manual_corners(points, 1000, 1200)
