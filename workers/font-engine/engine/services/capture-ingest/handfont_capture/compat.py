from __future__ import annotations

import sys
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
CAPTURE_ROOT = PACKAGE_DIR.parent
SERVICES_ROOT = CAPTURE_ROOT.parent
PROJECT_ROOT = SERVICES_ROOT.parent
IMAGE_PIPELINE_ROOT = SERVICES_ROOT / "image-pipeline"
VECTORIZER_ROOT = SERVICES_ROOT / "glyph-vectorizer"
HANGUL_ENGINE_ROOT = SERVICES_ROOT / "hangul-engine"

for path in (IMAGE_PIPELINE_ROOT, VECTORIZER_ROOT, HANGUL_ENGINE_ROOT):
    value = str(path)
    if value not in sys.path:
        sys.path.insert(0, value)
