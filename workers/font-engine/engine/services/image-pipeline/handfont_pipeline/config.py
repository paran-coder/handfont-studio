from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import CellLayout


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LAYOUT_PATH = PACKAGE_ROOT / "configs" / "template-layout-v1.3.0.json"
DEFAULT_MAPPING_PATH = PACKAGE_ROOT / "assets" / "character-set-v1.3.0.csv"
DEFAULT_BLANK_DIR = PACKAGE_ROOT / "assets" / "blank-pages"


def load_layout(path: Path | str = DEFAULT_LAYOUT_PATH) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_cells(layout: dict[str, Any]) -> list[CellLayout]:
    return [
        CellLayout(
            index=int(item["index"]),
            cell_id=str(item["cell_id"]),
            box_norm=tuple(float(v) for v in item["box_norm"]),
            writing_roi_norm=tuple(float(v) for v in item["writing_roi_norm"]),
        )
        for item in layout["cells"]
    ]
