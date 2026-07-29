from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np

from handfont_vectorizer.cli import main
from handfont_vectorizer.io import write_image


def test_batch_skips_empty_masks(tmp_path: Path) -> None:
    input_dir = tmp_path / "input"
    written = np.zeros((180, 180), dtype=np.uint8)
    cv2.putText(written, "A", (35, 145), cv2.FONT_HERSHEY_SIMPLEX, 4.0, 255, 12, cv2.LINE_AA)
    write_image(input_dir / "P01-C01" / "ink-mask.png", written)
    write_image(input_dir / "P01-C02" / "ink-mask.png", np.zeros_like(written))
    output = tmp_path / "output"
    exit_code = main(["batch", "--input-dir", str(input_dir), "--output", str(output)])
    summary = json.loads((output / "batch-summary.json").read_text(encoding="utf-8"))
    assert exit_code == 0
    assert summary["processed"] == 1
    assert summary["skipped"] == 1
    assert summary["failed"] == 0
