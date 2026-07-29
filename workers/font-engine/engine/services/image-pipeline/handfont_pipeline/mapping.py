from __future__ import annotations

import csv
from pathlib import Path


def load_page_mapping(path: Path | str, template_page: int) -> dict[str, dict[str, str]]:
    mapping: dict[str, dict[str, str]] = {}
    with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            try:
                row_page = int(row["template_page"])
            except (TypeError, ValueError):
                continue
            if row_page == template_page:
                mapping[row["cell_id"]] = row
    return mapping
