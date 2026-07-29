from handfont_fontbuilder.metrics import calculate_scale_and_advance, vertical_placement
from handfont_fontbuilder.models import FontBuildOptions


def test_vertical_classes():
    options = FontBuildOptions()
    assert vertical_placement("A", options).label == "cap"
    assert vertical_placement("x", options).label == "x-height"
    assert vertical_placement("g", options).bottom == -200
    assert vertical_placement("b", options).top == 700
    assert vertical_placement("_", options).top < 0


def test_advance_is_positive_and_rounded():
    scale, lsb, rsb, advance, placement = calculate_scale_and_advance("A", (10, 20, 210, 320), FontBuildOptions())
    assert scale > 0
    assert lsb >= 0 and rsb >= 0
    assert advance > 0 and advance % 10 == 0
    assert placement.top == 700


def test_hangul_uses_square_metrics():
    options = FontBuildOptions()
    scale, lsb, rsb, advance, placement = calculate_scale_and_advance("한", (0, 0, 400, 400), options)
    assert placement.label == "hangul-square"
    assert advance == 1000
    assert scale > 0
    assert lsb >= 40 and rsb >= 0
