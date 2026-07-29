from pathlib import Path

import cv2

from handfont_capture.identifier import PageIdentifier
from handfont_capture.compat import IMAGE_PIPELINE_ROOT  # noqa: F401
from handfont_pipeline.config import DEFAULT_BLANK_DIR
from handfont_pipeline.perspective import canonical_size


def test_identifies_all_blank_pages():
    identifier = PageIdentifier(dpi=150)
    width, height = canonical_size(150)
    for page in range(1, 10):
        image = cv2.imread(str(DEFAULT_BLANK_DIR / f"template-page-{page:02d}.png"))
        image = cv2.resize(image, (width, height), interpolation=cv2.INTER_AREA)
        result = identifier.identify(image)
        assert result.page == page
        assert result.confidence > 0.85
        assert result.margin > 0.02
