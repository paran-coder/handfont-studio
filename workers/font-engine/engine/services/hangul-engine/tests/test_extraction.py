import numpy as np

from handfont_hangul.extraction import extract_position_regions


def test_extracts_nonempty_regions_from_simple_vertical_mask():
    mask = np.zeros((100, 100), dtype=np.uint8)
    mask[10:70, 10:35] = 255
    mask[10:70, 60:75] = 255
    result = extract_position_regions("가", mask)
    assert len(result["components"]) == 2
    assert all(item["ink_pixels"] > 0 for item in result["components"])


def test_extracts_final_region():
    mask = np.zeros((100, 100), dtype=np.uint8)
    mask[5:55, 10:35] = 255
    mask[5:55, 60:75] = 255
    mask[70:90, 20:80] = 255
    result = extract_position_regions("각", mask)
    roles = {item["role"] for item in result["components"]}
    assert roles == {"choseong", "jungseong", "jongseong"}
    assert all(item["ink_pixels"] > 0 for item in result["components"])
