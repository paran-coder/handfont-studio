from pathlib import Path

import numpy as np
import pytest

from handfont_hangul_composer.composer import HangulComposer
from handfont_hangul_composer.library import TemplateLibrary


ROOT = Path(__file__).resolve().parents[2]
HANGUL_SOURCE = ROOT / "hangul-engine" / "examples" / "hangul-source-v1.6.0"


@pytest.fixture(scope="module")
def composer(tmp_path_factory):
    path = tmp_path_factory.mktemp("templates")
    library = TemplateLibrary.build(
        HANGUL_SOURCE / "hangul-position-map.json",
        HANGUL_SOURCE / "masks",
        path,
    )
    return HangulComposer(library)


def test_exact_and_fallback_composition(composer):
    exact_mask, exact_layers, exact_meta = composer.compose("갃")
    fallback_mask, fallback_layers, fallback_meta = composer.compose("쾅")
    assert exact_mask.shape == (480, 480)
    assert np.count_nonzero(exact_mask) > 1000
    assert len(exact_layers) == 3
    assert exact_meta["resolution"]["fallback_components"] == 0
    assert np.count_nonzero(fallback_mask) > 1000
    assert len(fallback_layers) == 3
    assert fallback_meta["resolution"]["fallback_components"] >= 1


def test_composition_is_deterministic(composer):
    left, _, left_meta = composer.compose("힣")
    right, _, right_meta = composer.compose("힣")
    assert np.array_equal(left, right)
    assert left_meta == right_meta
